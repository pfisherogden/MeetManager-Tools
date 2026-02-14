import argparse
import datetime
import json
import logging
import os
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# from access_parser import AccessParser DEPRECATED
try:
    from . import mdb_writer
except ImportError as e:
    logger.debug(f"Failed to import mdb_writer: {e}")
    mdb_writer: Any = None  # type: ignore


class MmToJsonConverter:
    def __init__(self, mdb_path=None, password=None, table_data=None):
        if mdb_path:
            if not os.path.exists(mdb_path):
                raise FileNotFoundError(f"MDB file not found: {mdb_path}")

            # Security: Prefer env var or arg over hardcoding
            if not password:
                password = os.environ.get("MM_DB_PASSWORD")

            logger.info(f"Loading database: {mdb_path}")

            # Initialize Jackcess
            if mdb_writer:
                mdb_writer.ensure_jvm_started()
                self.db = mdb_writer.open_db(mdb_path)
            else:
                raise ImportError("mdb_writer (Jackcess) is required for opening MDB files directly.")
        elif table_data is not None:
            self.db = None
        else:
            raise ValueError("Either mdb_path or table_data must be provided.")

        self.tables = {}
        self.cache_athlete_map = None
        self.cache_team_map = None
        self.cache_division_map = None
        self.schema_type = "A"  # A = Original C++ assumption, B = Singers23/Newer

        if table_data is not None:
            self._load_from_data(table_data)
        else:
            self._load_from_db()

    def _load_from_data(self, table_data):
        self.table_aliases = {
            "Meet": ["Meet", "MEET"],
            "Session": ["Session", "SESSIONS"],
            "Sessitem": ["Sessitem", "SESSITEM"],
            "Event": ["Event", "MTEVENT"],
            "Entry": ["Entry", "ENTRY"],
            "Relay": ["Relay", "RELAY"],
            "RelayNames": ["RelayNames", "RELAYNAMES"],
            "Athlete": ["Athlete", "ATHLETE"],
            "Team": ["Team", "TEAM"],
            "Divisions": ["Divisions", "DIVISIONS"],
        }

        # Determine schema type
        self.schema_type = "A"
        for candidate in ["MTEVENT", "mtevent"]:
            if candidate in table_data:
                self.schema_type = "B"
                break

        for logical, physical_candidates in self.table_aliases.items():
            found_data = None
            for candidate in physical_candidates:
                if candidate in table_data:
                    found_data = table_data[candidate]
                    break
                # Case insensitive check
                for k in table_data.keys():
                    if k.lower() == candidate.lower():
                        found_data = table_data[k]
                        break
                if found_data:
                    break

            if found_data is not None:
                df = pd.DataFrame(found_data)
                if not df.empty:
                    df.columns = df.columns.astype(str)
                self.tables[logical] = df
            else:
                self.tables[logical] = pd.DataFrame()

    def _get_val(self, row, key, default=""):
        """Safely retrieve value from a row, handling pandas NaN/None."""
        val = row.get(key)
        if pd.isna(val):
            return default
        return str(val).strip()

    def _load_from_db(self):
        # Pre-load required tables into Pandas DataFrames
        self.table_aliases = {
            "Meet": ["Meet", "MEET"],
            "Session": ["Session", "SESSIONS"],
            "Sessitem": ["Sessitem", "SESSITEM"],
            "Event": ["Event", "MTEVENT"],
            "Entry": ["Entry", "ENTRY"],
            "Relay": ["Relay", "RELAY"],
            "RelayNames": ["RelayNames", "RELAYNAMES"],
            "Athlete": ["Athlete", "ATHLETE"],
            "Team": ["Team", "TEAM"],
            "Divisions": ["Divisions", "DIVISIONS"],
        }

        # Jackcess
        catalog_tables = [str(t) for t in self.db.getTableNames()]
        catalog_map = {t.lower(): t for t in catalog_tables}

        for logical, physical_candidates in self.table_aliases.items():
            found_name = None
            for candidate in physical_candidates:
                if candidate.lower() in catalog_map:
                    found_name = catalog_map[candidate.lower()]
                    break

            if found_name:
                logger.debug(f"Parsing table {found_name}...")
                rows = None
                try:
                    # Detect Schema Type based on Event table name
                    if logical == "Event" and found_name == "MTEVENT":
                        self.schema_type = "B"
                        logger.info("Detected Schema Type B (MTEVENT structure)")

                    rows: Any = self._read_table_jackcess(found_name)  # type: ignore
                except Exception as e:
                    logger.error(f"Failed to parse table {found_name}: {e}")
                    logger.error("SKIPPING TABLE due to parse error.")
                    rows = None

                df = pd.DataFrame(rows)

                if not df.empty:
                    df.columns = df.columns.astype(str)

                self.tables[logical] = df
                logger.info(f"Loaded {logical} from {found_name} ({len(df)} rows)")
            else:
                # If Schema B, Sessitem might be missing, which is fine
                if logical not in ["Sessitem", "RelayNames", "Divisions"]:
                    logger.warning(f"Warning: Logical table {logical} not found (checked {physical_candidates}).")
                self.tables[logical] = pd.DataFrame()

    def _read_table_jackcess(self, table_name: str) -> list[dict[str, Any]] | None:
        import base64

        t = self.db.getTable(table_name)
        if t is None:
            return None

        columns = [str(c.getName()) for c in t.getColumns()]

        rows: list[dict[str, Any]] = []
        for row in t:
            row_data: dict[str, Any] = {}
            for cname in columns:
                val = row.get(cname)
                if val is None:
                    row_data[cname] = None
                elif isinstance(val, (int, float, str, bool)):
                    row_data[cname] = val
                else:
                    try:
                        type_name = str(type(val))
                        if "Date" in type_name:
                            try:
                                ts = val.getTime() / 1000.0
                                row_data[cname] = datetime.datetime.fromtimestamp(ts)
                            except Exception:
                                row_data[cname] = str(val)
                        elif "byte[]" in type_name or "jarray" in type_name:
                            try:
                                b = bytes(val)
                                row_data[cname] = base64.b64encode(b).decode("ascii")
                            except Exception:
                                row_data[cname] = str(val)
                        else:
                            row_data[cname] = str(val)
                    except Exception:
                        row_data[cname] = str(val)
            rows.append(row_data)
        return rows

    def convert(self) -> dict[str, Any]:
        meet = self.get_meet_info()
        sessions: list[Session] = self.get_session_info()

        if not sessions:
            if self.schema_type == "B":
                # In Schema B, columns might be different, but if get_session_info failed,
                # maybe it's because 'SESS_NO' vs 'SESSION'?
                pass
            else:
                sessions.append(self.create_default_session())

        # If we still have no sessions but have events, create default
        if not sessions and not self.tables["Event"].empty:
            sessions.append(self.create_default_session())

        meet_sessions_data = []

        for session in sessions:
            logger.debug(f"Processing session {session.sess_id} ({session.name})")
            events = self.get_events_by_session(session)
            logger.debug(f"Found {len(events)} events for session {session.sess_id}")
            session_events_data = []

            for event in events:
                event.create_description(meet["meetType"])
                self.add_entries_to_event(event)
                session_events_data.append(event.to_dict())

            session_data = session.to_dict()
            session_data["events"] = session_events_data
            meet_sessions_data.append(session_data)

        meet_data = meet.copy()
        meet_data["sessions"] = meet_sessions_data

        return meet_data

    def export_raw(self):
        """
        Exports the raw tables (sanitized) to a dictionary of lists.
        Used for the gRPC backend data source.
        """
        raw_data = {}
        # List of tables we care about for the API
        target_tables = [
            "Meet",
            "Team",
            "Athlete",
            "Event",
            "Session",
            "Sessitem",
            "Entry",
            "Relay",
            "RelayNames",
            "Divisions",
        ]

        for table_name in target_tables:
            df = self.tables.get(table_name)
            if df is not None and not df.empty:
                # Convert DataFrame to list of dicts
                # Replace NaNs with None/null for JSON compliance
                records = df.where(pd.notnull(df), None).to_dict(orient="records")
                raw_data[table_name] = records
            else:
                raw_data[table_name] = []

        return raw_data

    def create_default_session(self):
        """Creates a default session if none exist in the MDB."""
        return Session(sess_id=1, number=1, name="Session 1", day=1, start_time="08:00", is_default=True)

    # --- Data Retrieval Methods ---

    def get_meet_info(self):
        df = self.tables["Meet"]
        if df.empty:
            return {
                "meetName": "",
                "meetLocation": "",
                "meetStart": "",
                "meetEnd": "",
                "meetType": 0,
                "numLanes": 0,
            }

        row = df.iloc[0]

        if self.schema_type == "B":
            # Mapping for Schema B
            return {
                "meetName": self._get_val(row, "Meet"),
                "meetLocation": self._get_val(row, "Location"),
                "meetStart": self._get_val(row, "Start"),
                "meetEnd": self._get_val(row, "End"),
                "meetType": 0,
                "numLanes": 0,
            }
        else:
            return {
                "meetName": self._get_val(row, "Meet_name1"),
                "meetLocation": self._get_val(row, "Meet_location"),
                "meetStart": self._get_val(row, "Meet_start"),
                "meetEnd": self._get_val(row, "Meet_end"),
                "meetType": self._safe_int(row.get("Meet_class")),
                "numLanes": self._safe_int(row.get("Meet_numlanes")),
            }

    def get_session_info(self):
        df = self.tables["Session"]
        sessions: list[Session] = []
        if df.empty:
            return sessions

        if self.schema_type == "B":
            # Schema B: SESSIONS table
            # Cols: SESSION (Num), MAXIND, DAY, STARTTIME, SESSX
            if "SESSION" in df.columns:
                # Drop rows where SESSION is NaN
                df = df.dropna(subset=["SESSION"])
                df = df.sort_values("SESSION")

            for _, row in df.iterrows():
                try:
                    val = row.get("SESSION", 0)
                    if pd.isna(val):
                        continue
                    sess_num = self._safe_int(val)
                except Exception:
                    continue

                sess = Session(
                    sess_id=sess_num,  # ID is same as number here
                    number=sess_num,
                    name=f"Session {sess_num}",  # Name not explicitly in SESSIONS usually?
                    day=self._safe_int(row.get("DAY"), 1),
                    start_time=self._get_val(row, "STARTTIME", "09:00"),
                )
                sessions.append(sess)
        else:
            # Schema A
            if "Sess_no" in df.columns:
                df = df.sort_values("Sess_no")
            for _, row in df.iterrows():
                sess = Session(
                    sess_id=row.get("Sess_ptr"),
                    number=row.get("Sess_no"),
                    name=self._get_val(row, "Sess_name"),
                    day=row.get("Sess_day", 1),
                    start_time=row.get("Sess_starttime", 32400),
                )
                sessions.append(sess)
        return sessions

    def get_events_by_session(self, session):
        events = []
        if session.is_default:
            return self.get_all_events()

        if self.schema_type == "B":
            # Schema B: Link via MTEVENT.Session column
            df_evt = self.tables["Event"]
            if not df_evt.empty and "Session" in df_evt.columns:
                # Filter by session.sess_id (which is SESSION number in Schema B)
                # Ensure types match (float/int)
                target_sess = session.sess_id
                # Convert column to numeric for safety
                try:
                    df_evt["Session_Numeric"] = pd.to_numeric(df_evt["Session"], errors="coerce").fillna(0).astype(int)
                    sess_items = df_evt[df_evt["Session_Numeric"] == target_sess]
                except Exception:
                    sess_items = df_evt[df_evt["Session"] == target_sess]

                # Sort by event number
                if "MtEvent" in sess_items.columns:
                    sess_items = sess_items.sort_values("MtEvent")  # MtEvent is Event No

                for _, row in sess_items.iterrows():
                    evt = self._create_event_from_row(row, "F")
                    if evt:
                        events.append(evt)
        else:
            # Schema A: Link via Sessitem
            df_sessitem = self.tables["Sessitem"]
            if not df_sessitem.empty and "Sess_ptr" in df_sessitem.columns:
                target = session.sess_id
                items = df_sessitem[df_sessitem["Sess_ptr"] == target]
                if items.empty:
                    # Try string comparison just in case
                    items = df_sessitem[df_sessitem["Sess_ptr"].astype(str) == str(target)]

                if not items.empty:
                    logger.debug(f"Found {len(items)} events for session {target} in Sessitem")
                else:
                    logger.debug(f"No events found for session {target} in Sessitem (df size {len(df_sessitem)})")

                if "Sess_order" in items.columns:
                    items = items.sort_values("Sess_order")

                for _, item in items.iterrows():
                    evt_ptr = item.get("Event_ptr")
                    round_ltr = item.get("Sess_rnd")
                    event = self.get_event_by_id(evt_ptr, round_ltr)
                    if event:
                        events.append(event)
                    else:
                        logger.debug(f"Failed to find event_ptr {evt_ptr} in Event table")
        return events

    def get_all_events(self):
        events = []
        df = self.tables["Event"]
        if self.schema_type == "B":
            if not df.empty and "MtEvent" in df.columns:
                df = df.sort_values("MtEvent")
                for _, row in df.iterrows():
                    evt = self._create_event_from_row(row, "F")
                    if evt:
                        events.append(evt)
        else:
            if not df.empty and "Event_no" in df.columns:
                df = df.sort_values("Event_no")
                for _, row in df.iterrows():
                    evt = self._create_event_from_row(row, "F")
                    if evt:
                        events.append(evt)
        return events

    def get_event_by_id(self, event_ptr, round_ltr):
        df = self.tables["Event"]
        if self.schema_type == "B":
            # Should not be called if logic flows correctly for Schema B, but just in case
            if df.empty or "MtEv" not in df.columns:
                return None
            rows = df[df["MtEv"] == event_ptr]
            if rows.empty:
                return None
            return self._create_event_from_row(rows.iloc[0], round_ltr)
        else:
            if df.empty or "Event_ptr" not in df.columns:
                return None

            rows = df[df["Event_ptr"] == event_ptr]
            if rows.empty:
                return None

            return self._create_event_from_row(rows.iloc[0], round_ltr)

    def _create_event_from_row(self, row, round_ltr):
        if self.schema_type == "B":
            # Schema B Mapping
            # ['Meet', 'MtEv', 'MtEvX',            # fmt: off
            # Columns list: 'MtEvent', 'Distance', 'Stroke', 'Sex', 'I_R', 'Session',
            # 'Division', 'EventType', 'SESSX'
            # fmt: on

            relay = str(row.get("I_R", "I")) == "R"

            # Lo_Hi parsing
            lo_hi = self._safe_int(row.get("Lo_Hi"))
            min_age, max_age = self._parse_lo_hi(lo_hi)

            # Stroke
            stroke_val = row.get("Stroke")
            stroke_name = self.get_stroke(stroke_val, relay)

            # Division
            div_val = row.get("Division")
            division_name = str(div_val) if div_val else ""

            # Num Lanes? Default to 0 or 6/8 if unknown
            num_lanes = 0

            return Event(
                event_no=self._safe_int(row.get("MtEvent")),
                is_relay=relay,
                gender=self._get_val(row, "Sex"),
                gender_desc=self._get_val(row, "Sex"),
                min_age=min_age,
                max_age=max_age,
                distance=self._safe_int(row.get("Distance")),
                stroke=stroke_name,
                division=division_name,
                round_ltr=round_ltr,
                event_ptr=row.get("MtEvent"),  # Matches MtEvent in ENTRY
                num_lanes=num_lanes,
            )
        else:
            # Schema A Mapping
            relay = row.get("Ind_rel", "") == "R"

            pre_lanes = self._safe_int(row.get("Num_prelanes"))
            fin_lanes = self._safe_int(row.get("Num_finlanes"))
            evt_rounds = self._safe_int(row.get("Event_rounds"), 1)

            num_lanes = pre_lanes if evt_rounds == 1 else fin_lanes

            div_no = row.get("Div_no")
            division_name = self.get_division_name(div_no)

            stroke_char = self._get_val(row, "Event_stroke")
            stroke_name = self.get_stroke(stroke_char, relay)

            return Event(
                event_no=self._safe_int(row.get("Event_no")),
                is_relay=relay,
                gender=self._get_val(row, "Event_gender"),
                gender_desc=self._get_val(row, "Event_sex"),
                min_age=self._safe_int(row.get("Low_age") or row.get("Low_Age")),
                max_age=self._safe_int(row.get("High_age") or row.get("High_Age")),
                distance=self._safe_int(row.get("Event_dist")),
                stroke=stroke_name,
                division=division_name,
                round_ltr=round_ltr,
                event_ptr=row.get("Event_ptr"),
                num_lanes=num_lanes,
            )

    def _parse_lo_hi(self, val):
        # Heuristic: 8 -> 0-8, 78 -> 7-8, 910 -> 9-10, 1112 -> 11-12, 1314 -> 13-14, 1518 -> 15-18
        if val == 0:
            return 0, 109  # Open
        if val < 10:
            return 0, val  # e.g. 8 -> 8&U
        s = str(val)
        if len(s) == 2:  # 78 -> 7, 8
            return int(s[0]), int(s[1])
        if len(s) == 3:  # 910 -> 9, 10
            return int(s[0]), int(s[1:])
        if len(s) == 4:  # 1112 -> 11, 12
            return int(s[:2]), int(s[2:])
        return 0, 109  # Fallback

    def add_individual_entries(self, event):
        df = self.tables["Entry"]
        if df.empty:
            return

        if self.schema_type == "B":
            # Schema B: Link via MtEvent -> event.event_ptr (MtEv)
            if "MtEvent" in df.columns:
                entries = df[df["MtEvent"] == event.event_ptr]
                for _, row in entries.iterrows():
                    # Attempt to get time
                    score = float(row.get("Score", 0.0) or 0.0)
                    # Heuristic for Score to Time string
                    # If score > 100, assume centiseconds? e.g. 2425 -> 24.25
                    # Or assume it is time.
                    # Let's assume input is centiseconds if > 1000? Or just use raw logic
                    time_str = "NT"
                    if score > 0:
                        if score > 200:  # heuristic threshold
                            time_str = self.num_to_string(score / 100.0)
                        else:
                            time_str = self.num_to_string(score)

                    ath_no = row.get("Athlete")
                    athlete = self.get_athlete_by_number(ath_no)
                    if athlete:
                        event.add_entry(
                            {
                                "name": f"{athlete['first']} {athlete['last']}",
                                "age": athlete["age"],
                                "schoolYear": athlete["schoolYear"],
                                "team": athlete["team"],
                                "heat": self._safe_int(row.get("HEAT")),
                                "lane": self._safe_int(row.get("LANE")),
                                # Using Score as seed/time (unknown distinction in this schema)
                                "seedTime": time_str,
                                "psTime": "NT",
                                "athleteId": ath_no,
                                "teamId": athlete.get("teamId"),
                            }
                        )
        else:
            # Schema A
            if "Event_ptr" not in df.columns:
                return

            entries = df[df["Event_ptr"] == event.event_ptr]
            if not entries.empty:
                logger.debug(f"Found {len(entries)} entries for Event {event.event_no} (ptr {event.event_ptr})")
            for _, row in entries.iterrows():
                entry_info = self.get_heat_lane_time(event.round_ltr, event.stroke, row)
                if entry_info["heat"] != 0 and entry_info["lane"] != 0:
                    ath_no = row.get("Ath_no")
                    athlete = self.get_athlete_by_number(ath_no)
                    if athlete:
                        event.add_entry(
                            {
                                "name": f"{athlete['first']} {athlete['last']}",
                                "age": athlete["age"],
                                "schoolYear": athlete["schoolYear"],
                                "team": athlete["team"],
                                "heat": entry_info["heat"],
                                "lane": entry_info["lane"],
                                "seedTime": entry_info["seed"],
                                "psTime": entry_info["time"],
                                "finalTime": entry_info["time"],
                                "place": entry_info["place"],
                                "athleteId": ath_no,
                                "teamId": athlete.get("teamId"),
                            }
                        )

    def add_entries_to_event(self, event):
        if event.is_relay:
            self.add_relay_entries(event)
        else:
            self.add_individual_entries(event)

    def add_relay_entries(self, event):
        df = self.tables["Relay"]
        if df.empty:
            return

        if self.schema_type == "B":
            # Schema B Relay Logic
            # Assuming RELAY table has Event_ptr equivalent (MtEvent?)
            # debug_cols for RELAY wasn't run, but usually it matches ENTRY structure roughly
            # Let's check columns if possible, or assume 'MtEvent' like ENTRY
            if "MtEvent" in df.columns:
                entries = df[df["MtEvent"] == event.event_ptr]
                for _, row in entries.iterrows():
                    # Relay entries might be different in Schema B
                    # Just strict copy of what we have, improving as needed
                    # For now, assume similar to Individual but with Team

                    # Score/Time logic
                    score = float(row.get("Score", 0.0) or 0.0)
                    time_str = "NT"
                    if score > 0:
                        if score > 200:
                            time_str = self.num_to_string(score / 100.0)
                        else:
                            time_str = self.num_to_string(score)

                    team_no = row.get("Team")
                    team_name = self.get_team_name(team_no)

                    # Heat/Lane
                    heat = self._safe_int(row.get("HEAT"))
                    lane = self._safe_int(row.get("LANE"))

                    event.add_entry(
                        {
                            "name": self.get_relay_names_schema_b(event.event_ptr, team_no),  # Need helper
                            "team": team_name,
                            "heat": heat,
                            "lane": lane,
                            "seedTime": time_str,
                            "psTime": "NT",
                            "isRelay": True,
                            "relayLtr": str(row.get("RelayLtr", "A")),  # Guessing col name
                        }
                    )
        else:
            # Schema A
            if "Event_ptr" not in df.columns:
                return

            entries = df[df["Event_ptr"] == event.event_ptr]
            for _, row in entries.iterrows():
                entry_info = self.get_heat_lane_time(event.round_ltr, event.stroke, row)
                if entry_info["heat"] != 0 and entry_info["lane"] != 0:
                    team_no = row.get("Team_no")
                    team_name = self.get_team_name(team_no)
                    relay_ltr = row.get("Team_ltr", "A")

                    # Get Relay Athletes
                    relay_athletes = self.get_relay_athletes(event.event_ptr, team_no, relay_ltr, event.round_ltr)

                    # Format names: "F. Last"
                    swimmers_list = []
                    for a in relay_athletes:
                        initial = a["first"][0] if a["first"] else ""
                        swimmers_list.append(f"{initial}. {a['last']}")

                    names_str = ", ".join(swimmers_list)

                    event.add_entry(
                        {
                            "name": names_str,
                            "team": team_name,
                            "heat": entry_info["heat"],
                            "lane": entry_info["lane"],
                            "seedTime": entry_info["seed"],
                            "psTime": entry_info["time"],
                            "finalTime": entry_info["time"],
                            "place": entry_info["place"],
                            "isRelay": True,
                            "relayLtr": relay_ltr,
                            "relaySwimmers": swimmers_list,
                            "relayAthletes": relay_athletes,  # Full objects for extractor
                        }
                    )

    def get_relay_names_schema_b(self, event_ptr, team_no):
        # Stub for Schema B relay names if table differs
        # RELAYNAMES?
        return "Relay Team"

    def get_heat_lane_time(self, round_ltr, stroke, row):
        # Logic to pick Pre vs Fin columns
        seed_time = float(row.get("ConvSeed_time", 0.0) or 0.0)

        pre_heat = self._safe_int(row.get("Pre_heat"))
        pre_lane = self._safe_int(row.get("Pre_lane"))
        pre_time = float(row.get("Pre_Time", 0.0) or 0.0)
        pre_stat = str(row.get("Pre_Stat", "") or "")

        fin_heat = self._safe_int(row.get("Fin_heat"))
        fin_lane = self._safe_int(row.get("Fin_lane"))
        fin_time = float(row.get("Fin_Time", 0.0) or 0.0)
        fin_stat = str(row.get("Fin_Stat", "") or "")

        info = {}
        info["seed"] = self.num_to_string(seed_time) if seed_time > 0 else "NT"
        info["place"] = self._safe_int(row.get("Fin_place", row.get("Place", 0)))

        if round_ltr == "P":
            info["heat"] = pre_heat
            info["lane"] = pre_lane
            info["time"] = self.time_to_string(pre_time, pre_stat)
        else:
            info["heat"] = fin_heat
            info["lane"] = fin_lane
            info["time"] = self.time_to_string(fin_time, fin_stat)

        if stroke != "Diving":
            info["seed"] = self.time_to_min_sec(info["seed"])
            info["time"] = self.time_to_min_sec(info["time"])

        return info

    def get_relay_athletes(self, event_ptr, team_no, team_ltr, round_ltr):
        df = self.tables["RelayNames"]
        athletes: list[dict[str, Any]] = []
        if df.empty:
            return athletes

        # Filter
        mask = (
            (df["Event_ptr"] == event_ptr)
            & (df["Team_no"] == team_no)
            & (df["Team_ltr"] == team_ltr)
            & (df["Event_round"] == round_ltr)
        )
        rows = df[mask]
        for _, row in rows.iterrows():
            ath_no = row.get("Ath_no")
            ath = self.get_athlete_by_number(ath_no)
            if ath:
                athletes.append(ath)
        return athletes

    def get_stroke(self, stroke_id, is_relay):
        if not stroke_id:
            return ""
        sid = str(stroke_id)[0]

        # Numeric checks for Schema B
        if str(stroke_id) == "1":
            return "Freestyle"
        if str(stroke_id) == "2":
            return "Backstroke"
        if str(stroke_id) == "3":
            return "Breaststroke"
        if str(stroke_id) == "4":
            return "Butterfly"
        if str(stroke_id) == "5":
            return "Individual Medley" if not is_relay else "Medley"

        if sid == "A":
            return "Freestyle"
        if sid == "B":
            return "Backstroke"
        if sid == "C":
            return "Breaststroke"
        if sid == "D":
            return "Butterfly"
        if sid == "E":
            return "Medley" if is_relay else "Individual Medley"
        if sid == "F":
            return "Diving"
        return ""

    # --- Formatting Helpers ---

    # --- Lookup Helpers ---

    def get_athlete_by_number(self, ath_no):
        if self.cache_athlete_map is None:
            self.cache_athlete_map = {}
            df = self.tables["Athlete"]
            if not df.empty:
                for _, row in df.iterrows():
                    if self.schema_type == "B":
                        aid = row.get("Athlete")
                        team_no = row.get("Team1")
                        team_name = self.get_team_name(team_no)
                        self.cache_athlete_map[aid] = {
                            "first": self._get_val(row, "First"),
                            "last": self._get_val(row, "Last"),
                            "age": self._safe_int(row.get("Age")),
                            "schoolYear": self._get_val(row, "Class"),
                            "team": team_name,
                        }
                    else:
                        aid = row.get("Ath_no")
                        team_no = row.get("Team_no")
                        team_name = self.get_team_name(team_no)
                        self.cache_athlete_map[aid] = {
                            "first": self._get_val(row, "First_name"),
                            "last": self._get_val(row, "Last_name"),
                            "age": self._safe_int(row.get("Ath_age")),
                            "schoolYear": self._get_val(row, "Schl_yr"),
                            "team": team_name,
                        }
        return self.cache_athlete_map.get(ath_no)

    def get_team_name(self, team_no):
        if self.cache_team_map is None:
            self.cache_team_map = {}
            df = self.tables["Team"]
            if not df.empty:
                for _, row in df.iterrows():
                    if self.schema_type == "B":
                        tid = row.get("Team")
                        abbr = self._get_val(row, "TCode")
                        short = self._get_val(row, "Short")
                        lsc = self._get_val(row, "LSC")
                        name = short if short else f"{abbr}-{lsc}".strip("-")
                        self.cache_team_map[tid] = name
                    else:
                        tid = row.get("Team_no")
                        abbr = self._get_val(row, "Team_abbr")
                        short = self._get_val(row, "Team_short")
                        lsc = self._get_val(row, "Team_lsc")
                        name = short if short else f"{abbr}-{lsc}".strip("-")
                        self.cache_team_map[tid] = name
        return self.cache_team_map.get(team_no, "")

    def get_division_name(self, div_no):
        if self.cache_division_map is None:
            self.cache_division_map = {}
            df = self.tables["Divisions"]
            if not df.empty:
                for _, row in df.iterrows():
                    did = row.get("Div_no")
                    name = str(row.get("Div_name", "")).strip()
                    if name:
                        self.cache_division_map[did] = name
        return self.cache_division_map.get(div_no, "")

    def num_to_string(self, num):
        # replicate util.h numToString which prints "%.2f" for floats and "%d" for ints
        # But C++ overloaded it. seedTime is float.
        return f"{num:.2f}"

    def time_to_string(self, time_val, status):
        # logic from util.h
        if status and status.upper() == "SCR":
            return "SCR"
        if status and status.upper() == "DNS":
            return "DNS"
        if status and status.upper() == "DNF":
            return "DNF"
        if status and status.upper() == "DQ":
            return "DQ"
        if time_val == 0.0:
            return "NT"
        return f"{time_val:.2f}"

    def _safe_int(self, val, default=0):
        try:
            if pd.isna(val):
                return default
            return int(float(val))
        except (ValueError, TypeError):
            return default

    def time_to_min_sec(self, time_str):
        if not time_str or time_str in ["NT", "SCR", "DNS", "DNF", "DQ"]:
            return time_str
        try:
            val = float(time_str)
            seconds = int(val)
            cents = int(round((val - seconds) * 100))
            minutes = seconds // 60
            rem_seconds = seconds % 60

            if minutes > 0:
                return f"{minutes}:{rem_seconds:02d}.{cents:02d}"
            else:
                return f"{rem_seconds:02d}.{cents:02d}"
        except Exception:
            return time_str


class Session:
    def __init__(self, sess_id, number, name, day, start_time, is_default=False):
        self.sess_id = sess_id
        self.number = number
        self.name = name
        self.day = day
        self.start_time = start_time
        self.is_default = is_default

    def to_dict(self):
        return {
            "sessionNum": self.number,
            "sessionDay": self.day,
            "startTime": self.start_time,  # C++ passes raw int, client likely formats it
            "sessionDesc": self.name,
        }


class Event:
    def __init__(
        self,
        event_no,
        is_relay,
        gender,
        gender_desc,
        min_age,
        max_age,
        distance,
        stroke,
        division,
        round_ltr,
        event_ptr,
        num_lanes,
    ):
        self.event_no = event_no
        self.is_relay = is_relay
        self.gender = gender
        self.gender_desc = gender_desc  # e.g. "Boys"
        self.min_age = min_age
        self.max_age = max_age
        self.distance = distance
        self.stroke = stroke
        self.division = division
        self.round_ltr = round_ltr
        self.event_ptr = event_ptr
        self.num_lanes = num_lanes
        self.entries = []
        self.description = ""

    def create_description(self, meet_type):
        # Replicating Event::createDescription logic roughly

        # Gender Expansion
        gender_str = self.gender_desc
        if self.gender == "F":
            gender_str = "Girls"
        elif self.gender == "M":
            gender_str = "Boys"
        elif self.gender == "X":
            gender_str = "Mixed"

        # Age Group Formatting
        age_str = ""
        if self.min_age == 0 and self.max_age >= 109:
            age_str = "Open"
        elif self.min_age == 0:
            age_str = f"{self.max_age} & under"
        elif self.max_age >= 109:
            age_str = f"{self.min_age} & over"
        else:
            # Strict format "Min-Max" e.g. "11-12"
            age_str = f"{self.min_age}-{self.max_age}"

        # Distance & Stroke
        dist_str = f"{self.distance}"

        # Construct Description: "Girls 8 & Under 25 Yard Freestyle"
        # We need "Yard" or "Meter". Defaulting to "Yard" as per example unless we have course info.
        # Ideally this comes from meet info or event data, but often implicit in US summer leagues.

        self.description = f"{gender_str} {age_str} {dist_str} Yard {self.stroke}"

        if self.division:
            self.description += f" ({self.division})"

    def add_entry(self, entry_dict):
        self.entries.append(entry_dict)

    def to_dict(self):
        # Sort entries by heat, then lane
        sorted_entries = sorted(self.entries, key=lambda x: (x["heat"], x["lane"]))

        res = {
            "eventNum": self.event_no,
            "eventDesc": self.description,
            "isRelay": self.is_relay,
            "numLanes": self.num_lanes,
            "entries": sorted_entries,
        }
        return res


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    # Handle pandas types
    if "Timestamp" in str(type(obj)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def main():
    parser = argparse.ArgumentParser(description="mm_to_json (Python)")
    parser.add_argument("mdb_file", help="Path to the .mdb file")
    parser.add_argument("-d", "--output-dir", default="./", help="Directory for output (json) file")
    parser.add_argument(
        "-p",
        "--password",
        help="Database password (optional). Can also set MM_DB_PASSWORD env var.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Export raw tables instead of hierarchical session view.",
    )
    parser.add_argument("-w", "--watch", action="store_true", help="Watch the mdb_file (Not implemented)")

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a PDF report instead of JSON.",
    )
    parser.add_argument(
        "--report-type",
        choices=["psych", "entries", "lineups", "results", "timers", "program"],
        default="program",
        help="Type of report to generate.",
    )
    parser.add_argument(
        "--report-title",
        help="Custom title for the report.",
    )
    parser.add_argument(
        "--team-filter",
        help="Filter entries by team name.",
    )

    args = parser.parse_args()

    from .report_generator import ReportGenerator

    converter = MmToJsonConverter(args.mdb_file, args.password)
    try:
        if args.report:
            rg = ReportGenerator(converter, title=args.report_title)

            # Determine output filename
            base_name = os.path.splitext(os.path.basename(args.mdb_file))[0]
            out_path = os.path.join(args.output_dir, f"{base_name}_{args.report_type}.pdf")

            if args.report_type == "psych":
                rg.generate_psych_sheet(out_path)
            elif args.report_type == "entries":
                rg.generate_meet_entries(out_path, team_filter=args.team_filter)
            elif args.report_type == "lineups" or args.report_type == "program":
                rg.generate_meet_program(out_path)
            elif args.report_type == "results":
                rg.generate_meet_results(out_path)
            elif args.report_type == "timers":
                rg.generate_timer_sheets(out_path)

            logger.info(f"Successfully generated report to {out_path}")
            return

        if args.raw:
            data = converter.export_raw()
        else:
            data = converter.convert()

        # Determine output filename
        base_name = os.path.splitext(os.path.basename(args.mdb_file))[0]
        out_path = os.path.join(args.output_dir, f"{base_name}.json")

        with open(out_path, "w") as f:
            json.dump(data, f, indent=4, default=json_serial)

        logger.info(f"Successfully converted to {out_path}")

    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        logger.exception("Conversion traceback:")


if __name__ == "__main__":
    main()
