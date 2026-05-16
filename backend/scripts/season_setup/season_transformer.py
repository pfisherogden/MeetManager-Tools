import logging
import os
import json
import copy
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SeasonTransformer:
    def __init__(self, table_data: Dict[str, List[Dict[str, Any]]], table_defs: Optional[Dict[str, Any]] = None):
        """
        Initializes the SeasonTransformer with table data and optional definitions.
        table_data is a dictionary where keys are table names and values are lists of dictionaries (records).
        table_defs is a dictionary where keys are table names and values are table definitions (with columns).
        """
        self.table_data = {str(k): v for k, v in table_data.items()}
        self.table_defs = {str(k): v for k, v in table_defs.items()} if table_defs else {}
        self.team_ids = {} # Track team abbr -> ID
        
        # Standard table aliases to match MmToJsonConverter logic
        self.table_aliases = {
            "meet": ["Meet", "MEET", "meet"],
            "session": ["Session", "SESSIONS", "session"],
            "sessitem": ["Sessitem", "SESSITEM", "sessitem"],
            "event": ["Event", "MTEVENT", "event"],
            "entry": ["Entry", "ENTRY", "entry"],
            "relay": ["Relay", "RELAY", "relay"],
            "relaynames": ["RelayNames", "RELAYNAMES", "relaynames"],
            "athlete": ["athlete", "ATHLETE", "Athlete"],
            "team": ["Team", "TEAM", "team"],
            "divisions": ["Divisions", "DIVISIONS", "divisions"],
            "scoring": ["Scoring", "SCORING", "scoring"],
            "stdlanes": ["StdLanes", "STDLANES", "stdlanes"],
        }

    def _get_all_table_keys(self, logical_name: str) -> List[str]:
        """Finds all actual keys in table_data that match a logical table name (case-insensitive)."""
        candidates = set(c.lower() for c in self.table_aliases.get(logical_name, [logical_name]))
        found_keys = []
        for actual_key in self.table_data.keys():
            if str(actual_key).lower() in candidates:
                found_keys.append(actual_key)
        
        # Fallback: if no aliases match, check if logical_name itself matches case-insensitively
        if not found_keys:
            for actual_key in self.table_data.keys():
                if str(actual_key).lower() == logical_name.lower():
                    found_keys.append(actual_key)
                    
        return found_keys

    def _set_table(self, logical_name: str, records: List[Dict[str, Any]]):
        """Updates the records for a logical table name while preserving existing casing."""
        keys = self._get_all_table_keys(logical_name)
        if keys:
            for key in keys:
                self.table_data[key] = records
        else:
            # If not found, use the first alias as the default key
            default_key = self.table_aliases.get(logical_name, [logical_name])[0]
            self.table_data[default_key] = records

    def purge_data(self, preserve_team_abbr: str = "DP"):
        """
        Empties ATHLETE, ENTRY, RELAY, and RELAYNAMES tables.
        Filters TEAM table to keep only standard teams from venues.json or the preserved team.
        """
        logger.info(f"Purging data (preserving team: {preserve_team_abbr})")
        
        # transaction tables
        for logical in ["athlete", "entry", "relay", "relaynames"]:
            for key in self._get_all_table_keys(logical):
                self.table_data[key] = []

        standard_teams = {preserve_team_abbr.upper()}
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
            venues_path = os.path.join(config_dir, "venues.json")
            if os.path.exists(venues_path):
                with open(venues_path, "r") as f:
                    config = json.load(f)
                    for t in config.get("teams", {}).keys():
                        standard_teams.add(t.upper())
        except Exception as e:
            logger.warning(f"Could not load venues.json for team filtering: {e}")

        for key in self._get_all_table_keys("team"):
            teams = self.table_data[key]
            # Standard candidates for team abbreviation
            abbr_cols = ["tcode", "team_abbr", "abbr"]
            
            filtered_teams = []
            for t in teams:
                # Find the actual value for abbreviation in this record
                t_abbr = None
                t_id = None
                for k, v in t.items():
                    lk = str(k).lower()
                    if lk in abbr_cols:
                        t_abbr = str(v).strip().upper()
                    if lk in ["team", "team_no", "team_ptr"]:
                        t_id = v
                
                if t_abbr and t_abbr in standard_teams:
                    filtered_teams.append(t)
                    self.team_ids[t_abbr] = t_id
            
            self.table_data[key] = filtered_teams

    def _date_to_ms(self, date_str: str) -> Optional[int]:
        """Converts a date string (YYYY-MM-DD) to milliseconds since epoch."""
        if not date_str:
            return None
        try:
            # Handle already numeric or other formats if needed
            if isinstance(date_str, (int, float)):
                return int(date_str)
            
            # Try to parse YYYY-MM-DD
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(dt.timestamp() * 1000)
        except Exception as e:
            logger.warning(f"Could not parse date string {date_str}: {e}")
            return None

    def update_event_lanes(self, lanes: int):
        """Updates all events to use the specified number of lanes."""
        for key in self._get_all_table_keys("event"):
            events = self.table_data[key]
            logger.info(f"Updating {len(events)} events to {lanes} lanes")
            for event in events:
                # Update all common lane columns
                lane_cols = ["Num_prelanes", "Num_finlanes", "Num_semlanes", "Num_LanesInBestHeatsTimedFinal"]
                actual_cols = {k.lower(): k for k in event.keys()}
                
                for col in lane_cols:
                    if col.lower() in actual_cols:
                        event[actual_cols[col.lower()]] = lanes
                
                # Also set Std_lanes to 'A' (Automatic) to ensure seeding rules apply
                if "std_lanes" in actual_cols:
                    event[actual_cols["std_lanes"]] = "A"

    def update_meet(self, name: str, start_date: str, lanes: int, location: str = "", address: str = "", city: str = "", state: str = "", zip_code: str = "", age_up: str = "2026-06-01", entry_open: str = "", entry_deadline: str = "", owner_team: str = "DP", home_team: Optional[str] = None, away_team: Optional[str] = None, is_champs: bool = False):
        """Updates the MEET table metadata across all possible aliases."""
        # First, update all events to match pool lanes
        self.update_event_lanes(lanes)

        keys = self._get_all_table_keys("meet")
        if not keys:
            self._set_table("meet", [{}])
            keys = self._get_all_table_keys("meet")

        for key in keys:
            meet_table = self.table_data[key]
            if not meet_table:
                meet_table = [{}]
            
            mappings = {
                "name": ["meet_name1", "MEET_NAME1", "Meet_name1", "meet"],
                "start": ["meet_start", "MEET_START", "Meet_start", "start"],
                "end": ["meet_end", "MEET_END", "Meet_end", "end"],
                "lanes": ["meet_numlanes", "MEET_NUMLANES", "Meet_numlanes"],
                "age_up": ["calc_date", "CALC_DATE", "Calc_date"],
                "location": ["meet_location", "MEET_LOCATION", "Meet_location", "location"],
                "open": ["entry_opendate", "ENTRY_OPENDATE", "Entry_opendate", "entry_open"],
                "deadline": ["entry_deadline", "ENTRY_DEADLINE", "Entry_deadline"],
                "idformat": ["meet_idformat", "MEET_IDFORMAT"],
                "hostlsc": ["meet_hostlsc", "MEET_HOSTLSC"],
                "dqcodes": ["dqcodes_type", "DQCODES_TYPE"],
                "indmaxscorers": ["indmaxscorers_perteam", "INDMAXSCORERS_PERTEAM"],
                "relmaxscorers": ["relmaxscorers_perteam", "RELMAXSCORERS_PERTEAM"],
                "eligibility": ["entryeligibility_date", "ENTRYELIGIBILITY_DATE"],
                "entrymax_total": ["entrymax_total", "ENTRYMAX_TOTAL"],
                "indmax_perath": ["indmax_perath", "INDMAX_PERATH"],
                "relmax_perath": ["relmax_perath", "RELMAX_PERATH"],
                "addr1": ["meet_addr1", "MEET_ADDR1"],
                "city": ["meet_city", "MEET_CITY"],
                "state": ["meet_state", "MEET_STATE"],
                "zip": ["meet_zip", "MEET_ZIP"],
                "dual_evenodd": ["dual_evenodd", "DUAL_EVENODD"],
                "team_evenlanes": ["team_evenlanes", "TEAM_EVENLANES"],
                "team_oddlanes": ["team_oddlanes", "TEAM_ODDLANES"],
                "excludententries": ["excludententries_whenimporting", "EXCLUDENTENTRIES_WHENIMPORTING"]
            }

            home_id = self.team_ids.get(home_team.upper(), 0) if home_team else 0
            away_id = self.team_ids.get(away_team.upper(), 0) if away_team else 0

            values = {
                "name": name, 
                "start": self._date_to_ms(start_date), 
                "end": self._date_to_ms(start_date), 
                "lanes": lanes,
                "age_up": self._date_to_ms(age_up), 
                "location": location, 
                "open": self._date_to_ms(entry_open), 
                "deadline": self._date_to_ms(entry_deadline),
                "idformat": 1, # USAS
                "hostlsc": "CC",
                "dqcodes": "H", # Custom
                "indmaxscorers": 0 if is_champs else 4,
                "relmaxscorers": 1,
                "eligibility": self._date_to_ms(entry_open),
                "entrymax_total": 4,
                "indmax_perath": 3,
                "relmax_perath": 2,
                "addr1": address,
                "city": city,
                "state": state,
                "zip": zip_code,
                "dual_evenodd": bool(home_team and away_team) if not is_champs else False,
                "team_evenlanes": home_id if not is_champs else 0,
                "team_oddlanes": away_id if not is_champs else 0,
                "excludententries": False
            }

            # Lane assignments
            if home_team and away_team:
                for i in range(1, 13):
                    lane_key = f"dualteam_lane{i}"
                    # Home team in EVEN lanes (2, 4, 6...), Away team in ODD lanes (1, 3, 5...)
                    if i <= lanes:
                        values[lane_key] = home_id if i % 2 == 0 else away_id
                    else:
                        values[lane_key] = 0
                    mappings[lane_key] = [lane_key, lane_key.upper()]
            else:
                for i in range(1, 13):
                    lane_key = f"dualteam_lane{i}"
                    values[lane_key] = 0
                    mappings[lane_key] = [lane_key, lane_key.upper()]

            for record in meet_table:
                # Use a list of actual columns to be safe
                actual_cols = list(record.keys())
                # Ensure all mapped columns exist in the record if they are missing
                for prop, candidates in mappings.items():
                    found = False
                    for actual_col in actual_cols:
                        if str(actual_col).lower() in [c.lower() for c in candidates]:
                            found = True
                            if values.get(prop) is not None:
                                # Special case for boolean to match 2022 MDB (which used 1/0)
                                val = values[prop]
                                if isinstance(val, bool):
                                    val = 1 if val else 0
                                record[actual_col] = val
                            break
                    if not found and values.get(prop) is not None:
                        val = values[prop]
                        if isinstance(val, bool):
                            val = 1 if val else 0
                        record[candidates[0]] = val

    def setup_scoring_and_seeding(self, is_champs: bool = False):
        """Applies standard scoring and seeding rules."""
        for key in self._get_all_table_keys("scoring"):
            scoring = self.table_data[key]
            if scoring:
                if is_champs:
                    # Championship standard (16 places): 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1
                    # Confirmed via 2022-2025 historical data (User feedback)
                    ind_points = {
                        1: 20.0, 2: 17.0, 3: 16.0, 4: 15.0, 5: 14.0, 6: 13.0,
                        7: 12.0, 8: 11.0, 9: 9.0, 10: 7.0, 11: 6.0, 12: 5.0,
                        13: 4.0, 14: 3.0, 15: 2.0, 16: 1.0
                    }
                    # Relays (5 places): 40-34-32-30-28
                    rel_points = {
                        1: 40.0, 2: 34.0, 3: 32.0, 4: 30.0, 5: 28.0
                    }
                else:
                    # Dual meet standard: 5-3-2-1 for individual, 10-6 for relays
                    ind_points = {1: 5.0, 2: 3.0, 3: 2.0, 4: 1.0}
                    # Relays are usually 2x individual
                    rel_points = {k: v * 2 for k, v in ind_points.items()}
                
                for row in scoring:
                    actual_cols = {k.lower(): k for k in row.keys()}
                    
                    if "score_place" in actual_cols:
                        place = row[actual_cols["score_place"]]
                        if "ind_score" in actual_cols:
                            row[actual_cols["ind_score"]] = ind_points.get(place, 0.0)
                        if "rel_score" in actual_cols:
                            row[actual_cols["rel_score"]] = rel_points.get(place, 0.0)
                    else:
                        # Fallback for ind1, ind2, ... structure (up to 16 places for Champs)
                        points_list = [ind_points.get(i, 0.0) for i in range(1, 17)]
                        for i, val in enumerate(points_list, 1):
                            target = f"ind{i}"
                            if target in actual_cols:
                                row[actual_cols[target]] = val
                        
                        rel_list = [rel_points.get(i, 0.0) for i in range(1, 17)]
                        for i, val in enumerate(rel_list, 1):
                            target = f"rel{i}"
                            if target in actual_cols:
                                row[actual_cols[target]] = val

    def ensure_std_lanes(self):
        """Ensures the StdLanes table contains standard seeding orders for 1-12 lanes."""
        # Standard seeding orders for pools
        # 6 lanes: 3, 4, 2, 5, 1, 6
        # 8 lanes: 4, 5, 3, 6, 2, 7, 1, 8
        # ...
        standard_orders = {
            1: [1],
            2: [1, 2],
            3: [2, 3, 1],
            4: [2, 3, 1, 4],
            5: [3, 4, 2, 5, 1],
            6: [3, 4, 2, 5, 1, 6],
            7: [4, 5, 3, 6, 2, 7, 1],
            8: [4, 5, 3, 6, 2, 7, 1, 8],
            9: [5, 6, 4, 7, 3, 8, 2, 9, 1],
            10: [5, 6, 4, 7, 3, 8, 2, 9, 1, 10],
            11: [6, 7, 5, 8, 4, 9, 3, 10, 2, 11, 1],
            12: [6, 7, 5, 8, 4, 9, 3, 10, 2, 11, 1, 12]
        }

        new_rows = []
        for tot, order in standard_orders.items():
            row = {"tot_lanes": tot, "Lanes": tot}
            for i in range(1, 13):
                val = order[i-1] if i <= len(order) else 0
                # Standard Meet Manager column names for StdLanes are usually Order1, Order2...
                row[f"Order{i}"] = val
                # Fallback to order_01 etc if that's what's in the template
                row[f"order_{i:02d}"] = val
            new_rows.append(row)

        self._set_table("stdlanes", new_rows)

    def consolidate_sessions(self, is_champs: bool = False):
        """
        Consolidates events into sessions.
        - For non-champs: All events into a single "All" session.
        - For champs: Multiple sessions based on event type.
        """
        session_keys = self._get_all_table_keys("session")
        sessitem_keys = self._get_all_table_keys("sessitem")
        event_keys = self._get_all_table_keys("event")

        # Clear existing sessions and sessitems
        for key in session_keys: self.table_data[key] = []
        for key in sessitem_keys: self.table_data[key] = []

        if not is_champs:
            logger.info("Consolidating sessions into 'Session 1'")
            sess_ptr = 1
            new_session = {
                "Sess_no": 1, "Sess_ltr": " ", "Sess_ptr": sess_ptr, "Sess_day": 1,
                "Sess_starttime": 32400, "Sess_name": "All", "Sess_interval": 60,
                "Sess_course": "Y", "Sess_entrymax": 0, "Sess_entrymaxind": 0,
                "Sess_entrymaxrel": 0, "Sess_backinterval": 15, "Sess_divinginterval": 30,
                "Sess_chaseinterval": 0
            }
            self._set_table("session", [new_session])

            new_sessitems = []
            if event_keys:
                events = self.table_data[event_keys[0]]
                for i, event in enumerate(events, 1):
                    # Robustly find Event_ptr (could be MtEvent in some schemas)
                    actual_cols = {k.lower(): k for k in event.keys()}
                    e_ptr = i
                    if "event_ptr" in actual_cols:
                        e_ptr = event[actual_cols["event_ptr"]]
                    elif "mtevent" in actual_cols:
                        e_ptr = event[actual_cols["mtevent"]]

                    new_sessitems.append({
                        "Sess_order": i, "Sess_ptr": sess_ptr, "Event_ptr": e_ptr,
                        "Sess_rnd": "F", "Rept_type": " ", "Delay_seconds": 0, "Alt_With": False
                    })
                    # Link event to session if column exists
                    if "session" in actual_cols:
                        event[actual_cols["session"]] = sess_ptr

            self._set_table("sessitem", new_sessitems)
            return

        # CHAMPS LOGIC
        logger.info("Creating multi-session layout for Champs")
        # Define sessions based on 2025 Champs MDB
        champs_sessions = [
            {"name": "Med Relays", "stroke": "E", "ind_rel": "R", "start": 32400},
            {"name": "Freestyle", "stroke": "A", "ind_rel": "I", "start": 34560},
            {"name": "Butterfly", "stroke": "D", "ind_rel": "I", "start": 37440},
            {"name": "Breaststroke", "stroke": "C", "ind_rel": "I", "start": 39540},
            {"name": "Individual Medley", "stroke": "E", "ind_rel": "I", "start": 42600},
            {"name": "Backstroke", "stroke": "B", "ind_rel": "I", "start": 45120},
            {"name": "Freestyle Relays", "stroke": "A", "ind_rel": "R", "start": 48120},
        ]

        session_records = []
        new_sessitems = []
        events = self.table_data[event_keys[0]] if event_keys else []
        logger.info(f"Distributing {len(events)} events into {len(champs_sessions)} sessions")
        
        for i, s_def in enumerate(champs_sessions, 1):
            sess_ptr = i
            session_records.append({
                "Sess_no": i, "Sess_ltr": " ", "Sess_ptr": sess_ptr, "Sess_day": 1,
                "Sess_starttime": s_def["start"], "Sess_name": s_def["name"], "Sess_interval": 20,
                "Sess_course": "Y", "Sess_entrymax": 0, "Sess_entrymaxind": 0,
                "Sess_entrymaxrel": 0, "Sess_backinterval": 10, "Sess_divinginterval": 30,
                "Sess_chaseinterval": 0
            })

            # Find matching events
            sess_events = []
            for event in events:
                actual_cols = {k.lower(): k for k in event.keys()}
                e_stroke = str(event.get(actual_cols.get("event_stroke"), "")).strip().upper()
                e_indrel = str(event.get(actual_cols.get("ind_rel"), "")).strip().upper()
                
                if e_stroke == s_def["stroke"] and e_indrel == s_def["ind_rel"]:
                    sess_events.append(event)
                    # Link event to session if column exists
                    if "session" in actual_cols:
                        event[actual_cols["session"]] = sess_ptr
            
            # Sort by event_no to preserve order
            def get_event_no(x):
                ac = {k.lower(): k for k in x.keys()}
                for cand in ["event_no", "mtev"]:
                    if cand in ac:
                        return int(x[ac[cand]] or 0)
                return 0
            sess_events.sort(key=get_event_no)

            for j, event in enumerate(sess_events, 1):
                actual_cols = {k.lower(): k for k in event.keys()}
                e_ptr = 0
                if "event_ptr" in actual_cols:
                    e_ptr = event[actual_cols["event_ptr"]]
                elif "mtevent" in actual_cols:
                    e_ptr = event[actual_cols["mtevent"]]
                
                new_sessitems.append({
                    "Sess_order": j, "Sess_ptr": sess_ptr, "Event_ptr": e_ptr,
                    "Sess_rnd": "F", "Rept_type": "H", "Delay_seconds": 0, "Alt_With": False
                })

        logger.info(f"Created {len(session_records)} sessions and {len(new_sessitems)} session items")
        self._set_table("session", session_records)
        self._set_table("sessitem", new_sessitems)

    def ensure_team_exists(self, abbr: str, name: str):
        """Ensures a team exists in the TEAM table across all aliases."""
        team_keys = self._get_all_table_keys("team")
        if not team_keys:
            self._set_table("team", [])
            team_keys = self._get_all_table_keys("team")

        for key in team_keys:
            teams = self.table_data[key]
            # Robust exists check
            abbr_cols = ["tcode", "team_abbr", "abbr"]
            existing_id = None
            for t in teams:
                found_abbr = None
                found_id = None
                for k, v in t.items():
                    lk = str(k).lower()
                    if lk in abbr_cols:
                        found_abbr = str(v).strip().upper()
                    if lk in ["team", "team_no", "team_ptr"]:
                        found_id = v
                
                if found_abbr == str(abbr).strip().upper():
                    existing_id = found_id
                    break
            
            if existing_id is not None:
                self.team_ids[abbr.upper()] = existing_id
            else:
                logger.info(f"Adding missing team: {abbr} ({name}) to {key}")
                
                matched_team = {}
                max_no = 0
                for t in teams:
                    for k, v in t.items():
                        if str(k).lower() in ["team", "team_no", "team_ptr"] and v:
                            try: max_no = max(max_no, int(v))
                            except: pass
                
                new_id = max_no + 1
                template_rec = None
                if teams: 
                    template_rec = teams[0]
                elif key in self.table_defs:
                    template_rec = {c["name"]: None for c in self.table_defs[key].get("columns", [])}
                
                if template_rec:
                    for k, v in template_rec.items():
                        lk = k.lower()
                        if lk in ["tcode", "team_abbr", "abbr"]: matched_team[k] = abbr
                        elif lk in ["tname", "team_name", "name"]: matched_team[k] = name
                        elif lk in ["short", "team_short", "short_name"]: matched_team[k] = name[:15]
                        elif lk in ["lsc", "team_lsc"]: matched_team[k] = "CC"
                        elif lk in ["ttype", "team_type"]: matched_team[k] = "AGE"
                        elif lk in ["team", "team_no", "team_ptr"]: matched_team[k] = new_id
                        elif lk == "team_gender": matched_team[k] = "B"
                        else: matched_team[k] = template_rec.get(k)
                    teams.append(matched_team)
                else:
                    new_team = {
                        "TCode": abbr, "TName": name, "Short": name[:15],
                        "LSC": "CC", "TType": "AGE", "Team_no": new_id
                    }
                    teams.append(new_team)
                
                self.team_ids[abbr.upper()] = new_id
                self.table_data[key] = teams
