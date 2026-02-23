from __future__ import annotations

import datetime
import io
import json
import logging
import os
import tempfile
from concurrent import futures
from typing import Any

import grpc

# Import generated classes
try:
    from meetmanager.v1 import meet_manager_pb2 as pb2
    from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc
except ImportError:
    # Fallback for environments where protos aren't generated yet
    # We use cast to Any to avoid mypy errors when this fallback is active
    import typing

    pb2 = typing.cast(Any, None)
    pb2_grpc = typing.cast(Any, None)
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from auth_interceptor import FirebaseAuthInterceptor
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer
from storage_provider import GCSStorageProvider, LocalStorageProvider, StorageProvider

# Defines where the source JSON data lives
DATA_DIR = "../data"
SOURCE_FILE = "Sample_Data.json"
CONFIG_FILE = "config.json"


class MeetManagerService(pb2_grpc.MeetManagerServiceServicer):
    def __init__(self):
        # Initialize storage provider
        self.storage: StorageProvider
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if bucket_name:
            self.storage = GCSStorageProvider(bucket_name)
        else:
            base_storage_dir = os.path.join(os.path.dirname(__file__), DATA_DIR)
            self.storage = LocalStorageProvider(base_storage_dir)

        # Cache structure: {uid: {'filename': str, 'mtime': float, 'data': dict}}
        self._user_cache: dict[str, dict[str, Any]] = {}
        self.current_file = SOURCE_FILE
        # Note: We don't load data in __init__ anymore because it's per-user
        # self._load_data()
        # self._load_config()

    def _get_user_path(self, context, filename=""):
        uid = self._check_auth(context)
        return os.path.join("users", uid, filename)

    def _check_auth(self, context):
        """Helper to ensure the request is authenticated."""
        # Allow disabling auth for local dev/testing
        if os.getenv("GRPC_AUTH_DISABLED") == "true":
            return "dev-user"

        uid = getattr(context, "uid", None)
        if uid is None:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication required")
        return uid

    def _load_user_config(self, context):
        uid = self._check_auth(context)
        config_path = os.path.join("users", uid, CONFIG_FILE)
        if self.storage.exists(config_path):
            with tempfile.NamedTemporaryFile() as tmp:
                self.storage.download_file(config_path, tmp.name)
                with open(tmp.name) as f:
                    return json.load(f)
        return {"meet_name": "", "meet_description": "", "active_dataset": SOURCE_FILE}

    def _save_user_config(self, context, config):
        uid = self._check_auth(context)
        config_path = os.path.join("users", uid, CONFIG_FILE)
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            json.dump(config, tmp, indent=2)
            tmp_path = tmp.name
        try:
            self.storage.upload_file(tmp_path, config_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _load_user_data(self, context):
        config = self._load_user_config(context)
        filename = config.get("active_dataset", SOURCE_FILE)
        uid = self._check_auth(context)

        user_path = os.path.join("users", uid, filename)
        # Check cache
        if uid in self._user_cache:
            entry = self._user_cache[uid]
            if entry['filename'] == filename:
                # Check if modified
                try:
                    mtime = self.storage.get_last_modified(user_path)
                    if mtime == entry['mtime']:
                        return entry['data'], config
                except Exception:
                    pass # Force reload on error

        if not self.storage.exists(user_path):
            # Fallback for prototype: check global Sample_Data.json
            if self.storage.exists(SOURCE_FILE):
                user_path = SOURCE_FILE
            else:
                return {}, config

        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
            tmp_path = tmp.name
        try:
            self.storage.download_file(user_path, tmp_path)
            if filename.endswith(".mdb"):
                cache = self._load_mdb(tmp_path)
            else:
                with open(tmp_path) as f:
                    cache = json.load(f)
            
            # Update cache
            try:
                mtime = self.storage.get_last_modified(user_path)
                self._user_cache[uid] = {'filename': filename, 'mtime': mtime, 'data': cache}
            except Exception as e:
                print(f"Failed to update cache: {e}")

            return cache, config
        except Exception as e:
            print(f"Error loading user data: {e}")
            return {}, config
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _load_mdb(self, path):
        """Parsing MDB using MmToJsonConverter (Jackcess/JPype) for performance."""
        # Copy to temp file to avoid locking issues
        with tempfile.NamedTemporaryFile(suffix=".mdb", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with open(path, "rb") as src, open(tmp_path, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)

            converter = MmToJsonConverter(mdb_path=tmp_path)
            # MmToJsonConverter loads data into self.tables (dict of DataFrames)
            cache = {}
            for table_name, df in converter.tables.items():
                # Convert DataFrame to list of dicts, ensuring all values are strings/primitives
                # The existing server logic expects strings for most things, but MmToJsonConverter
                # might produce ints/floats.
                # We'll convert to dicts and let Python handle types, but be aware of mismatch.
                records = df.to_dict("records")
                cache[table_name] = records

            return cache
        except Exception as e:
            print(f"Error loading MDB: {e}")
            return {}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def UploadDataset(self, request_iterator, context):
        print("DEBUG: UploadDataset called", flush=True)
        uid = self._check_auth(context)
        filename = "uploaded.mdb"

        # Temporary buffer to hold file content
        file_content = io.BytesIO()

        try:
            for request in request_iterator:
                if request.HasField("filename"):
                    filename = os.path.basename(request.filename)
                    if not filename.lower().endswith(".mdb"):
                        filename += ".mdb"

                if request.HasField("chunk"):
                    file_content.write(request.chunk)

            # Upload to storage provider
            user_path = os.path.join("users", uid, filename)
            with tempfile.NamedTemporaryFile(suffix=".mdb", delete=False) as tmp:
                tmp.write(file_content.getvalue())
                tmp_path = tmp.name

            try:
                self.storage.upload_file(tmp_path, user_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            print(f"Saved uploaded file to {user_path}")

            # Update active dataset in config
            config = self._load_user_config(context)
            config["active_dataset"] = filename
            self._save_user_config(context, config)

            return pb2.UploadDatasetResponse(success=True, message=f"Saved {filename}")
        except Exception as e:
            print(f"Upload failed: {e}")
            return pb2.UploadDatasetResponse(success=False, message=str(e))

    def GetDashboardStats(self, request, context):
        request = request or pb2.GetDashboardStatsRequest()
        cache, _ = self._load_user_data(context)

        def _t(n):
            return cache.get(n, [])

        teams = _t("Team")
        athletes = _t("Athlete")
        events = _t("Event")
        meets = _t("Meet")

        return pb2.GetDashboardStatsResponse(
            meet_count=len(meets), team_count=len(teams), athlete_count=len(athletes), event_count=len(events)
        )

    def GetMeets(self, request, context):
        request = request or pb2.GetMeetsRequest()
        cache, _ = self._load_user_data(context)
        data = cache.get("Meet", [])
        meets = []
        for item in data:
            name = item.get("Meet_name") or item.get("MName") or "Unknown Meet"
            loc = item.get("Location") or item.get("Meet_location") or ""
            start = self._format_date(item.get("Start") or item.get("Start_date") or "")
            end = self._format_date(item.get("End") or item.get("End_date") or "")

            meets.append(pb2.Meet(id="1", name=name, location=loc, start_date=start, end_date=end, status="active"))
        return pb2.GetMeetsResponse(meets=meets)

    def GetTeams(self, request, context):
        request = request or pb2.GetTeamsRequest()
        cache, _ = self._load_user_data(context)
        data = cache.get("Team", [])
        athletes = cache.get("Athlete", [])

        # Count athletes per team
        ath_counts: dict[int, int] = {}
        for ath in athletes:
            t_id = int(ath.get("Team_no", 0))
            ath_counts[t_id] = ath_counts.get(t_id, 0) + 1

        teams = []
        for item in data:
            t_id = int(item.get("Team_no", 0))
            teams.append(
                pb2.Team(
                    id=t_id,
                    name=item.get("Team_name", "Unknown"),
                    code=item.get("Team_abbr", ""),
                    lsc=item.get("Team_lsc", ""),
                    city=item.get("Team_city", ""),
                    state=item.get("Team_statenew", ""),
                    athlete_count=ath_counts.get(t_id, 0),
                )
            )
        return pb2.GetTeamsResponse(teams=teams)

    def GetTeam(self, request, context):
        request = request or pb2.GetTeamRequest()
        team_id = request.id
        cache, _ = self._load_user_data(context)
        data = cache.get("Team", [])
        athlete_data = cache.get("Athlete", [])
        athlete_counts: dict[int, int] = {}
        for a in athlete_data:
            t_no = self._safe_int(a.get("Team_no") or a.get("team_no"))
            if t_no:
                athlete_counts[t_no] = athlete_counts.get(t_no, 0) + 1

        for item in data:
            if int(item.get("Team_no", 0)) == team_id:
                return pb2.GetTeamResponse(
                    team=pb2.Team(
                        id=int(item.get("Team_no", 0)),
                        name=item.get("Team_name", "Unknown"),
                        code=item.get("Team_abbr", ""),
                        lsc=item.get("Team_lsc", ""),
                        city=item.get("Team_city", ""),
                        state=item.get("Team_statenew", ""),
                        athlete_count=athlete_counts.get(team_id, 0),
                    )
                )

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Team {team_id} not found")
        return pb2.GetTeamResponse()

    def GetAthletes(self, request, context):
        request = request or pb2.GetAthletesRequest()
        cache, _ = self._load_user_data(context)
        data = cache.get("Athlete", [])
        teams_map = {int(t.get("Team_no", 0)): t.get("Team_name") for t in cache.get("Team", [])}

        athletes = []
        for item in data:
            t_id = int(item.get("Team_no", 0))
            if request and request.team_id and str(t_id) != request.team_id:
                continue

            dob_raw = item.get("Ath_birthdate") or item.get("Birth_date") or ""
            dob = dob_raw.split(" ")[0] if dob_raw else ""

            athletes.append(
                pb2.Athlete(
                    id=int(item.get("Ath_no", 0)),
                    first_name=item.get("First_name", ""),
                    last_name=item.get("Last_name", ""),
                    gender=item.get("Ath_Sex", ""),
                    age=int(item.get("Ath_age", 0)),
                    team_id=t_id,
                    team_name=teams_map.get(t_id, "Unknown"),
                    school_year=item.get("School_yr", ""),
                    reg_no=item.get("Reg_no", ""),
                    date_of_birth=dob,
                )
            )
        return pb2.GetAthletesResponse(athletes=athletes)

    def GetAthlete(self, request, context):
        request = request or pb2.GetAthleteRequest()
        ath_id = request.id
        cache, _ = self._load_user_data(context)
        data = cache.get("Athlete", [])
        teams_map = {int(t.get("Team_no", 0)): t.get("Team_name") for t in cache.get("Team", [])}

        for item in data:
            if int(item.get("Ath_no", 0)) == ath_id:
                t_id = int(item.get("Team_no", 0))
                return pb2.GetAthleteResponse(
                    athlete=pb2.Athlete(
                        id=int(item.get("Ath_no", 0)),
                        first_name=item.get("First_name", ""),
                        last_name=item.get("Last_name", ""),
                        gender=item.get("Ath_Sex", ""),
                        age=int(item.get("Ath_age", 0)),
                        team_id=t_id,
                        team_name=teams_map.get(t_id, "Unknown"),
                        school_year=item.get("School_yr", ""),
                        reg_no=item.get("Reg_no", ""),
                    )
                )

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Athlete {ath_id} not found")
        return pb2.GetAthleteResponse()

    def GetEvents(self, request, context):
        request = request or pb2.GetEventsRequest()
        cache, _ = self._load_user_data(context)
        data = cache.get("Event", [])
        events = []
        stroke_map = {"A": "Freestyle", "B": "Backstroke", "C": "Breaststroke", "D": "Butterfly", "E": "IM"}
        gender_map = {"B": "Boys", "G": "Girls", "X": "Mixed", "M": "Men", "F": "Women", "W": "Women"}

        entry_counts: dict[str, int] = {}
        entries = cache.get("Entry", []) or cache.get("ENTRY", [])
        for e in entries:
            evt_ptr = e.get("Event_ptr")
            if evt_ptr:
                entry_counts[evt_ptr] = entry_counts.get(evt_ptr, 0) + 1

        relays = cache.get("Relay", []) or cache.get("RELAY", [])
        for r in relays:
            evt_ptr = r.get("Event_ptr")
            if evt_ptr:
                entry_counts[evt_ptr] = entry_counts.get(evt_ptr, 0) + 1

        # Build session mapping from Sessitem (Linking Event_ptr to Session No)
        sess_map = {}
        sessitem_table = cache.get("Sessitem", []) or cache.get("SESSITEM", [])
        session_table = cache.get("Session", []) or cache.get("SESSIONS", [])

        # ptr_to_no: Sess_ptr -> Sess_no
        ptr_to_no = {s.get("Sess_ptr"): self._safe_int(s.get("Sess_no", 1)) for s in session_table if s.get("Sess_ptr")}

        for si in sessitem_table:
            e_ptr = si.get("Event_ptr")
            s_ptr = si.get("Sess_ptr")
            if e_ptr and s_ptr:
                sess_map[e_ptr] = ptr_to_no.get(s_ptr, 1)

        for item in data:
            raw_stroke = item.get("Event_stroke", "").upper().strip()
            stroke_desc = stroke_map.get(raw_stroke, raw_stroke)

            is_relay = item.get("Ind_rel", "").upper().strip() == "R"
            if raw_stroke == "E" and is_relay:
                stroke_desc = "Medley Relay"
            elif is_relay and stroke_desc != raw_stroke:
                stroke_desc += " Relay"

            raw_gender = item.get("Event_sex", "").upper().strip()
            gender_desc = gender_map.get(raw_gender, raw_gender)

            # Map Session: Use Sessitem map if Event.Sess_no is missing
            e_ptr = item.get("Event_ptr") or item.get("Event_no")
            sess_no = self._safe_int(item.get("Sess_no"))
            if not sess_no and e_ptr:
                sess_no = sess_map.get(e_ptr, 1)

            events.append(
                pb2.Event(
                    id=int(item.get("Event_no", 0)),
                    gender=gender_desc,
                    distance=int(item.get("Event_dist", 0)),
                    stroke=stroke_desc,
                    low_age=int(item.get("Low_age", 0)),
                    high_age=int(item.get("High_Age", 0)),
                    session=max(1, sess_no),
                    entry_count=entry_counts.get(item.get("Event_no") or item.get("Event_ptr"), 0),
                    age_group=self._format_age(item.get("Low_age"), item.get("High_Age")),
                )
            )
        return pb2.GetEventsResponse(events=events)

    def ListDatasets(self, request, context):
        request = request or pb2.ListDatasetsRequest()
        uid = self._check_auth(context)
        config = self._load_user_config(context)
        active_file = config.get("active_dataset", SOURCE_FILE)

        datasets = []
        try:
            # List files from users/[uid]/
            user_prefix = os.path.join("users", uid)
            files = self.storage.list_files(user_prefix)

            # Also include default Sample_Data.json if it exists and user has no files?
            # For simplicity, let's just list user's files

            for rel_path in files:
                filename = os.path.basename(rel_path)
                if filename.endswith(".json") or filename.endswith(".mdb"):
                    # We don't easily get mod time from all storage providers without extra calls
                    # For local, it's easy. For GCS, we need blob.updated.
                    # For now, placeholder or 0
                    mod_time = "0"
                    is_active = filename == active_file
                    datasets.append(pb2.Dataset(filename=filename, is_active=is_active, last_modified=mod_time))

            # Always include Sample_Data.json if nothing else
            if not datasets and self.storage.exists(SOURCE_FILE):
                datasets.append(
                    pb2.Dataset(filename=SOURCE_FILE, is_active=(active_file == SOURCE_FILE), last_modified="0")
                )

        except Exception as e:
            print(f"Error listing datasets: {e}")

        return pb2.ListDatasetsResponse(datasets=datasets)

    def SetActiveDataset(self, request, context):
        request = request or pb2.SetActiveDatasetRequest()
        uid = self._check_auth(context)
        filename = os.path.basename(request.filename)

        if not (filename.endswith(".mdb") or filename.endswith(".json")):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Invalid file type")
            return pb2.SetActiveDatasetResponse()

        user_path = os.path.join("users", uid, filename)
        if not self.storage.exists(user_path) and not (filename == SOURCE_FILE and self.storage.exists(SOURCE_FILE)):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"File {filename} not found.")
            return pb2.SetActiveDatasetResponse()

        print(f"Switching user {uid} dataset to {filename}...")
        config = self._load_user_config(context)
        config["active_dataset"] = filename
        self._save_user_config(context, config)
        return pb2.SetActiveDatasetResponse()

    def ClearDataset(self, request, context):
        request = request or pb2.ClearDatasetRequest()
        uid = self._check_auth(context)
        filename = os.path.basename(request.filename)
        if not (filename.endswith(".mdb") or filename.endswith(".json")):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Invalid file type")
            return pb2.ClearDatasetResponse()

        user_path = os.path.join("users", uid, filename)
        if not self.storage.exists(user_path):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"File {filename} not found.")
            return pb2.ClearDatasetResponse()

        try:
            self.storage.delete_file(user_path)
            config = self._load_user_config(context)
            if config.get("active_dataset") == filename:
                config["active_dataset"] = SOURCE_FILE
                self._save_user_config(context, config)

        except Exception as e:
            print(f"Error deleting dataset {filename}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to delete file: {str(e)}")

        return pb2.ClearDatasetResponse()

    def ClearAllDatasets(self, request, context):
        request = request or pb2.ClearAllDatasetsRequest()
        uid = self._check_auth(context)
        try:
            user_prefix = os.path.join("users", uid)
            files = self.storage.list_files(user_prefix)
            for rel_path in files:
                filename = os.path.basename(rel_path)
                if filename == CONFIG_FILE:
                    continue
                if filename.endswith(".mdb") or filename.endswith(".json"):
                    self.storage.delete_file(rel_path)

            config = self._load_user_config(context)
            config["active_dataset"] = SOURCE_FILE
            self._save_user_config(context, config)

        except Exception as e:
            print(f"Error clearing datasets: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to clear datasets: {str(e)}")

        return pb2.ClearAllDatasetsResponse()

    def _format_date(self, date_str):
        if not date_str:
            return ""
        try:
            date_str = str(date_str).strip()
            if " " in date_str:
                date_str = date_str.split(" ")[0]

            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%y"):
                try:
                    dt = datetime.datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return date_str
        except Exception:
            return str(date_str)

    def GetRelays(self, request, context):
        request = request or pb2.GetRelaysRequest()
        cache, _ = self._load_user_data(context)
        relays_data = cache.get("Relay", [])
        if not relays_data:
            relays_data = cache.get("RELAY", [])

        relay_names_data = cache.get("RelayNames", []) or cache.get("RELAYNAMES", [])
        relay_legs_map: dict[tuple[Any, Any, Any], list[Any]] = {}
        for rn in relay_names_data:
            key = (rn.get("Event_ptr"), rn.get("Team_no"), rn.get("Relay_no"))
            if key not in relay_legs_map:
                relay_legs_map[key] = []
            relay_legs_map[key].append(rn)

        teams = {t.get("Team_no"): t.get("Team_name") for t in cache.get("Team", [])}
        athletes = {a.get("Ath_no"): a for a in cache.get("Athlete", [])}

        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {"B": "Boys", "G": "Girls", "X": "Mixed", "M": "Men", "W": "Women", "F": "Women"}

        for e in cache.get("Event", []):
            e_no = e.get("Event_no") or e.get("Event_ptr")
            if e_no:
                g = gender_map.get(e.get("Event_sex", "").strip(), e.get("Event_sex", ""))
                d = e.get("Event_dist", "")
                s = stroke_map.get(e.get("Event_stroke", "").strip(), e.get("Event_stroke", ""))
                age_group = self._format_age(e.get("Low_age"), e.get("High_Age"))
                name = f"{g} {age_group} {d} {s}"
                events_map[e_no] = name

        result = []
        for idx, item in enumerate(relays_data):
            t_id = item.get("Team_ptr", 0)
            if not t_id or t_id == "0":
                t_id = item.get("Team_no", 0)

            event_ptr = item.get("Event_ptr")
            relay_no = item.get("Relay_no")

            legs = relay_legs_map.get((event_ptr, t_id, relay_no), [])
            legs.sort(key=lambda x: int(x.get("Pos_no", 0) if str(x.get("Pos_no")).strip().isdigit() else 99))

            leg_names = ["", "", "", ""]
            for leg in legs:
                try:
                    pos = int(leg.get("Pos_no", 0))
                    if 1 <= pos <= 4:
                        ath_id = leg.get("Ath_no")
                        ath = athletes.get(ath_id)
                        if ath:
                            leg_names[pos - 1] = f"{ath.get('First_name', '')} {ath.get('Last_name', '')}"
                except ValueError:
                    continue

            seed = item.get("ActualSeed_time") or item.get("ConvSeed_time") or item.get("Seed_Time") or "NT"
            try:
                if float(seed) == 0:
                    seed = "NT"
            except (ValueError, TypeError):
                pass

            result.append(
                pb2.Relay(
                    id=idx,
                    event_id=self._safe_int(item.get("Event_ptr")),
                    team_id=self._safe_int(t_id),
                    team_name=teams.get(t_id, "Unknown"),
                    leg1_name=leg_names[0],
                    leg2_name=leg_names[1],
                    leg3_name=leg_names[2],
                    leg4_name=leg_names[3],
                    seed_time=str(seed),
                    final_time=str(item.get("Fin_Time", "")),
                    place=self._safe_int(item.get("Fin_place", item.get("Place"))),
                    event_name=events_map.get(event_ptr, f"Event {event_ptr}"),
                    relay_letter=item.get("Team_ltr", ""),
                    heat=self._safe_int(item.get("Fin_heat")),
                    lane=self._safe_int(item.get("Fin_lane")),
                )
            )
        return pb2.GetRelaysResponse(relays=result)

    def GetScores(self, request, context):
        request = request or pb2.GetScoresRequest()
        cache, config = self._load_user_data(context)

        teams_data = cache.get("Team", [])
        teams = {t.get("Team_no"): {"name": t.get("Team_name"), "id": t.get("Team_no")} for t in teams_data}
        scores = {t_id: {"ind": 0.0, "rel": 0.0} for t_id in teams}

        entries_data = cache.get("Entry", []) or cache.get("ENTRY", [])
        athletes = {a.get("Ath_no"): a for a in cache.get("Athlete", [])}
        events_sex_map = {
            e.get("Event_no") or e.get("Event_ptr"): e.get("Event_sex", "M") for e in cache.get("Event", [])
        }

        if entries_data:
            for e in entries_data:
                ath_id = e.get("Ath_no")
                ath = athletes.get(ath_id)
                if ath:
                    t_id = ath.get("Team_no")
                    if t_id in scores:
                        e_id = e.get("Event_ptr")
                        sex = events_sex_map.get(e_id, ath.get("Ath_Sex", "M"))
                        val = self._calculate_points(e, sex, False, cache)
                        scores[t_id]["ind"] += val

        relays_data = cache.get("Relay", []) or cache.get("RELAY", [])
        if relays_data:
            for r in relays_data:
                t_id = r.get("Team_no")
                if not t_id or t_id == "0":
                    t_id = r.get("Team_ptr")

                if t_id in scores:
                    e_id = r.get("Event_ptr")
                    sex = events_sex_map.get(e_id, r.get("Rel_sex", "X"))
                    val = self._calculate_points(r, sex, True, cache)
                    scores[t_id]["rel"] += val

        result = []
        for t_id, s in scores.items():
            total = s["ind"] + s["rel"]
            result.append(
                pb2.Score(
                    team_id=self._safe_int(t_id),
                    team_name=teams[t_id]["name"],
                    individual_points=s["ind"],
                    relay_points=s["rel"],
                    total_points=total,
                    rank=0,
                    meet_name=config.get("meet_name", "Unknown Meet"),
                )
            )

        result.sort(key=lambda x: x.total_points, reverse=True)
        for i, r in enumerate(result):
            if r.total_points > 0:
                r.rank = i + 1

        return pb2.GetScoresResponse(scores=result)

    def GetEntries(self, request, context):
        request = request or pb2.GetEntriesRequest()
        cache, _ = self._load_user_data(context)
        entries_data = cache.get("Entry", []) or cache.get("ENTRY", [])

        athletes = {a.get("Ath_no"): a for a in cache.get("Athlete", [])}
        teams = {t.get("Team_no"): t.get("Team_name") for t in cache.get("Team", [])}
        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {"B": "Boys", "G": "Girls", "X": "Mixed", "M": "Men", "W": "Women", "F": "Women"}

        for e in cache.get("Event", []):
            e_no = e.get("Event_no") or e.get("Event_ptr")
            if e_no:
                g = gender_map.get(e.get("Event_sex", "").strip(), e.get("Event_sex", ""))
                d = e.get("Event_dist", "")
                s = stroke_map.get(e.get("Event_stroke", "").strip(), e.get("Event_stroke", ""))
                age_group = self._format_age(e.get("Low_age"), e.get("High_Age"))
                name = f"{g} {age_group} {d} {s}"
                events_map[e_no] = name

        result = []
        for idx, item in enumerate(entries_data):
            ath_id = item.get("Ath_no", 0)
            if request and request.athlete_id and str(ath_id) != request.athlete_id:
                continue

            athlete = athletes.get(ath_id, {})
            t_id = athlete.get("Team_no", 0)
            event_id = item.get("Event_ptr")
            if request and request.event_id and str(event_id) != request.event_id:
                continue

            seed = item.get("ActualSeed_time") or item.get("ConvSeed_time") or item.get("Seed_Time") or "NT"
            try:
                if float(seed) == 0:
                    seed = "NT"
            except (ValueError, TypeError):
                pass

            entry_id_val = item.get("Entry_no")
            final_id = int(entry_id_val) if entry_id_val else idx

            result.append(
                pb2.Entry(
                    id=final_id,
                    event_id=self._safe_int(event_id),
                    athlete_id=self._safe_int(ath_id),
                    athlete_name=f"{athlete.get('First_name', '')} {athlete.get('Last_name', '')}",
                    team_id=self._safe_int(t_id),
                    team_name=teams.get(t_id, "Unknown"),
                    seed_time=str(seed),
                    final_time=str(item.get("Fin_Time", "")),
                    place=self._safe_int(item.get("Fin_place", item.get("Place"))),
                    event_name=events_map.get(event_id, f"Event {event_id}"),
                    heat=self._safe_int(item.get("Fin_heat", item.get("Pre_heat", 0))),
                    lane=self._safe_int(item.get("Fin_lane", item.get("Pre_lane", 0))),
                    points=self._safe_float(item.get("Ev_score", 0.0)),
                )
            )
        return pb2.GetEntriesResponse(entries=result)

    def _get_scoring_map(self, cache):
        scoring_data = cache.get("Scoring", []) or cache.get("SCORING", [])
        scoring_map: dict[str, dict[str, dict[int, dict[str, float]]]] = {}
        for row in scoring_data:
            div = row.get("score_divno", "0")
            sex = row.get("score_sex", "M").upper()
            place = self._safe_int(row.get("score_place", 0))

            if div not in scoring_map:
                scoring_map[div] = {}
            if sex not in scoring_map[div]:
                scoring_map[div][sex] = {}

            scoring_map[div][sex][place] = {
                "ind": self._safe_float(row.get("ind_score", 0)),
                "rel": self._safe_float(row.get("rel_score", 0)),
            }
        return scoring_map

    def _format_age(self, low, high):
        """Standardize age group naming (e.g., 6 & under)."""
        low = self._safe_int(low)
        high = self._safe_int(high)
        if low == 0 and high >= 109:
            return "Open"
        if low == 0:
            return f"{high} & under"
        if high >= 109:
            return f"{low} & over"
        return f"{low}-{high}"

    def _calculate_points(self, item, sex, is_relay, cache):
        score = self._safe_float(item.get("Ev_score", 0))
        if score > 0:
            return score

        place = self._safe_int(item.get("Fin_place", item.get("Place", 0)))
        if place <= 0:
            return 0.0

        div = item.get("Div_no", "0") or "0"
        sex_map = {"B": "M", "M": "M", "G": "F", "W": "F", "F": "F", "X": "M"}
        mapped_sex = sex_map.get(sex.upper(), "M")

        scoring_map = self._get_scoring_map(cache)
        div_map = scoring_map.get(div, scoring_map.get("0", {}))
        sex_scores = div_map.get(mapped_sex, div_map.get("M", {}))

        score_data = sex_scores.get(place, {})
        return score_data.get("rel" if is_relay else "ind", 0.0)

    def GetEventScores(self, request, context):
        request = request or pb2.GetEventScoresRequest()
        cache, _ = self._load_user_data(context)
        entries = cache.get("Entry", []) or cache.get("ENTRY", [])
        relays = cache.get("Relay", []) or cache.get("RELAY", [])
        athletes_map = {a.get("Ath_no"): a for a in cache.get("Athlete", [])}
        teams_map = {t.get("Team_no"): t.get("Team_name") for t in cache.get("Team", [])}

        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {"B": "Boys", "G": "Girls", "X": "Mixed", "M": "Men", "W": "Women", "F": "Women"}

        event_dict: dict[str, dict[str, Any]] = {}
        event_raw_map = {}

        for e in cache.get("Event", []):
            e_no = e.get("Event_no") or e.get("Event_ptr")
            if not e_no:
                continue

            event_raw_map[e_no] = e
            g = gender_map.get(e.get("Event_sex", "").strip(), e.get("Event_sex", ""))
            d = e.get("Event_dist", "")
            s_raw = e.get("Event_stroke", "").strip()
            s = stroke_map.get(s_raw, s_raw)

            is_relay = e.get("Ind_rel", "").upper().strip() == "R"
            if s_raw == "E" and is_relay:
                s = "Medley Relay"
            elif is_relay and s != s_raw:
                s += " Relay"

            low = e.get("Low_age", "")
            high = e.get("High_Age", "")
            age_group = self._format_age(low, high)
            name = f"{g} {age_group} {d} {s}"
            events_map[e_no] = name
            event_dict[e_no] = {"id": int(e_no), "name": name, "entries": []}

        for item in entries:
            e_id = item.get("Event_ptr")
            if e_id not in event_dict:
                continue

            ath_id = item.get("Ath_no")
            ath = athletes_map.get(ath_id)
            t_id = ath.get("Team_no", 0) if ath else 0
            place = self._safe_int(item.get("Fin_place", item.get("Place", 0)))

            ev_raw = event_raw_map.get(e_id, {})
            points = self._calculate_points(item, ev_raw.get("Event_sex", "M"), False, cache)

            if not item.get("Fin_Time") and place <= 0:
                continue

            seed = item.get("ActualSeed_time") or item.get("ConvSeed_time") or item.get("Seed_Time") or "NT"
            try:
                if float(seed) == 0:
                    seed = "NT"
            except (ValueError, TypeError):
                pass

            entry_obj = pb2.Entry(
                id=0,
                event_id=int(e_id),
                athlete_id=int(ath_id if ath else 0),
                athlete_name=f"{ath.get('First_name', '')} {ath.get('Last_name', '')}" if ath else "Unknown",
                team_id=int(t_id),
                team_name=teams_map.get(t_id, "Unknown"),
                seed_time=str(seed),
                final_time=str(item.get("Fin_Time", "")),
                place=place,
                points=points,
                event_name=events_map.get(e_id, ""),
            )
            event_dict[e_id]["entries"].append(entry_obj)

        for item in relays:
            e_id = item.get("Event_ptr")
            if e_id not in event_dict:
                continue

            t_id = item.get("Team_ptr") or item.get("Team_no")
            place = self._safe_int(item.get("Fin_place", item.get("Place", 0)))
            rel_ltr = item.get("Team_ltr", "")

            ev_raw = event_raw_map.get(e_id, {})
            points = self._calculate_points(item, ev_raw.get("Event_sex", "X"), True, cache)

            if not item.get("Fin_Time") and place <= 0:
                continue

            seed = item.get("ActualSeed_time") or item.get("ConvSeed_time") or item.get("Seed_Time") or "NT"
            try:
                if float(seed) == 0:
                    seed = "NT"
            except (ValueError, TypeError):
                pass

            entry_obj = pb2.Entry(
                id=0,
                event_id=int(e_id),
                athlete_id=0,
                athlete_name=f"Relay Team ({rel_ltr})" if rel_ltr else "Relay Team",
                team_id=int(t_id if t_id else 0),
                team_name=teams_map.get(t_id, "Unknown"),
                seed_time=str(seed),
                final_time=str(item.get("Fin_Time", "")),
                place=place,
                points=points,
                heat=self._safe_int(item.get("Fin_heat", 0)),
                lane=self._safe_int(item.get("Fin_lane", 0)),
                event_name=events_map.get(e_id, ""),
            )
            event_dict[e_id]["entries"].append(entry_obj)

        resp_list = []
        sorted_keys = sorted(event_dict.keys(), key=lambda k: int(k))
        for k in sorted_keys:
            ev = event_dict[k]
            ev["entries"].sort(key=lambda x: x.place if x.place > 0 else 9999)

            resp_list.append(pb2.EventScore(event_id=ev["id"], event_name=ev["name"], entries=ev["entries"]))

        return pb2.GetEventScoresResponse(event_scores=resp_list)

    def GenerateReport(self, request, context):
        if request is None:
            return pb2.GenerateReportResponse(success=False, message="Missing request")
        try:
            cache, _ = self._load_user_data(context)
            converter = MmToJsonConverter(table_data=cache)

            rtype_val = pb2.REPORT_TYPE_PSYCH_UNSPECIFIED
            team_filter = None
            title = None
            gender_filter = None
            age_group_filter = None
            columns_on_page = 2
            show_relay_swimmers = True
            zebra_striping = False

            if request:
                rtype_val = request.type
                team_filter = request.team_filter
                title = request.title
                gender_filter = request.gender_filter
                age_group_filter = request.age_group_filter
                if request.columns_on_page:
                    columns_on_page = request.columns_on_page
                if request.HasField("show_relay_swimmers"):
                    show_relay_swimmers = request.show_relay_swimmers
                if request.HasField("zebra_striping"):
                    zebra_striping = request.zebra_striping

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                temp_path = tmp.name

            rtype_map = {
                pb2.REPORT_TYPE_PSYCH_UNSPECIFIED: "psych",
                pb2.REPORT_TYPE_ENTRIES: "entries",
                pb2.REPORT_TYPE_LINEUPS: "lineups",
                pb2.REPORT_TYPE_RESULTS: "results",
                pb2.REPORT_TYPE_MEET_PROGRAM: "program",
                pb2.REPORT_TYPE_MEET_PROGRAM_HTML: "program_html",
                pb2.REPORT_TYPE_ENTRIES_HYTEK: "entries_hytek",
                pb2.REPORT_TYPE_ENTRIES_CLUB: "entries_club",
            }

            rtype = rtype_map.get(rtype_val, "psych")
            pdf_content = b""
            html_content = None

            extractor = ReportDataExtractor(converter)
            renderer = WeasyRenderer(temp_path)

            if rtype == "psych":
                report_data = extractor.extract_psych_sheet_data(
                    team_filter=team_filter,
                    report_title=title,
                    gender_filter=gender_filter,
                    age_group_filter=age_group_filter,
                )
                report_data["zebra_striping"] = zebra_striping
                renderer.render_entries(report_data, "psych_sheet.html")
            elif rtype == "entries":
                report_data = extractor.extract_meet_entries_data(
                    team_filter=team_filter,
                    report_title=title,
                    gender_filter=gender_filter,
                    age_group_filter=age_group_filter,
                )
                report_data["zebra_striping"] = zebra_striping
                renderer.render_entries(report_data, "entries_hytek.html")
            elif rtype == "lineups":
                report_data = extractor.extract_timer_sheets_data(
                    team_filter=team_filter,
                    report_title=title,
                    gender_filter=gender_filter,
                    age_group_filter=age_group_filter,
                )
                report_data["zebra_striping"] = zebra_striping
                renderer.render_entries(report_data, "lineups.html")
            elif rtype == "results":
                report_data = extractor.extract_results_data(
                    team_filter=team_filter,
                    report_title=title,
                    gender_filter=gender_filter,
                    age_group_filter=age_group_filter,
                )
                report_data["zebra_striping"] = zebra_striping
                renderer.render_entries(report_data, "results.html")
            elif rtype == "program":
                program_data = extractor.extract_meet_program_data(
                    team_filter=team_filter,
                    report_title=title,
                    gender_filter=gender_filter,
                    age_group_filter=age_group_filter,
                    columns_on_page=columns_on_page,
                    show_relay_swimmers=show_relay_swimmers,
                )
                program_data["zebra_striping"] = zebra_striping
                renderer.render_meet_program(program_data)
            elif rtype == "program_html":
                program_data = extractor.extract_meet_program_data(
                    team_filter=team_filter,
                    report_title=title,
                    gender_filter=gender_filter,
                    age_group_filter=age_group_filter,
                    columns_on_page=columns_on_page,
                    show_relay_swimmers=show_relay_swimmers,
                )
                program_data["zebra_striping"] = zebra_striping
                html_content = renderer.render_to_html(program_data)
                with open(temp_path, "wb") as f:
                    f.write(b"")
            elif rtype == "entries_hytek":
                report_data = extractor.extract_meet_entries_data(
                    team_filter=team_filter,
                    report_title=title,
                    gender_filter=gender_filter,
                    age_group_filter=age_group_filter,
                )
                report_data["zebra_striping"] = zebra_striping
                renderer.render_entries(report_data, "entries_hytek.html")
            elif rtype == "entries_club":
                report_data = extractor.extract_meet_entries_data(
                    team_filter=team_filter,
                    report_title=title,
                    gender_filter=gender_filter,
                    age_group_filter=age_group_filter,
                )
                report_data["zebra_striping"] = zebra_striping
                renderer.render_entries(report_data, "entries_club.html")

            if os.path.exists(temp_path):
                with open(temp_path, "rb") as f:
                    pdf_content = f.read()
                os.remove(temp_path)

            filename = f"report_{rtype}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            if rtype == "program_html":
                filename = filename.replace(".pdf", ".html")

            return pb2.GenerateReportResponse(
                success=True,
                message="Report generated successfully",
                pdf_content=pdf_content,
                filename=filename,
                html_content=html_content,
            )

        except Exception as e:
            print(f"Error generating report: {e}")
            return pb2.GenerateReportResponse(success=False, message=str(e))

    def GenerateReportBundle(self, request, context):
        import zipfile

        if request is None:
            return pb2.GenerateReportBundleResponse(success=False, message="Missing request")

        try:
            cache, _ = self._load_user_data(context)
            converter = MmToJsonConverter(table_data=cache)
            extractor = ReportDataExtractor(converter)

            rtype_map = {
                pb2.REPORT_TYPE_PSYCH_UNSPECIFIED: "psych",
                pb2.REPORT_TYPE_ENTRIES: "entries",
                pb2.REPORT_TYPE_LINEUPS: "lineups",
                pb2.REPORT_TYPE_RESULTS: "results",
                pb2.REPORT_TYPE_MEET_PROGRAM: "program",
                pb2.REPORT_TYPE_MEET_PROGRAM_HTML: "program_html",
                pb2.REPORT_TYPE_ENTRIES_HYTEK: "entries_hytek",
                pb2.REPORT_TYPE_ENTRIES_CLUB: "entries_club",
            }

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, report_req in enumerate(request.reports):
                    rtype_val = report_req.type
                    rtype = rtype_map.get(rtype_val, "psych")
                    title = report_req.title
                    team_filter = report_req.team_filter
                    gender_filter = report_req.gender_filter
                    age_group_filter = report_req.age_group_filter

                    # New variation fields
                    columns_on_page = 2
                    if report_req.columns_on_page:
                        columns_on_page = report_req.columns_on_page

                    show_relay_swimmers = True
                    if report_req.HasField("show_relay_swimmers"):
                        show_relay_swimmers = report_req.show_relay_swimmers

                    zebra_striping = False
                    if report_req.HasField("zebra_striping"):
                        zebra_striping = report_req.zebra_striping

                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        temp_path = tmp.name

                    renderer = WeasyRenderer(temp_path)

                    if rtype == "psych":
                        report_data = extractor.extract_psych_sheet_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "psych_sheet.html")
                    elif rtype == "entries":
                        report_data = extractor.extract_meet_entries_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "entries_hytek.html")
                    elif rtype == "lineups":
                        report_data = extractor.extract_timer_sheets_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "lineups.html")
                    elif rtype == "results":
                        report_data = extractor.extract_results_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "results.html")
                    elif rtype == "program":
                        program_data = extractor.extract_meet_program_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                            columns_on_page=columns_on_page,
                            show_relay_swimmers=show_relay_swimmers,
                        )
                        program_data["zebra_striping"] = zebra_striping
                        renderer.render_meet_program(program_data)
                    elif rtype == "program_html":
                        program_data = extractor.extract_meet_program_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                            columns_on_page=columns_on_page,
                            show_relay_swimmers=show_relay_swimmers,
                        )
                        program_data["zebra_striping"] = zebra_striping
                        html_content = renderer.render_to_html(program_data)
                        with open(temp_path, "w") as f:
                            f.write(html_content)
                    elif rtype == "entries_hytek":
                        report_data = extractor.extract_meet_entries_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "entries_hytek.html")
                    elif rtype == "entries_club":
                        report_data = extractor.extract_meet_entries_data(
                            team_filter=team_filter,
                            report_title=title,
                            gender_filter=gender_filter,
                            age_group_filter=age_group_filter,
                        )
                        report_data["zebra_striping"] = zebra_striping
                        renderer.render_entries(report_data, "entries_club.html")

                    if os.path.exists(temp_path):
                        # Clean title for filename
                        safe_title = "".join(c for c in (title or rtype) if c.isalnum() or c in (" ", "_", "-")).strip()
                        ext = ".html" if rtype == "program_html" else ".pdf"
                        file_name = f"{idx + 1}_{safe_title}{ext}"
                        zip_file.write(temp_path, file_name)
                        os.remove(temp_path)

            bundle_name = request.bundle_name or f"meet_bundle_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            if not bundle_name.endswith(".zip"):
                bundle_name += ".zip"

            return pb2.GenerateReportBundleResponse(
                success=True,
                message="Bundle generated successfully",
                zip_content=zip_buffer.getvalue(),
                filename=bundle_name,
            )

        except Exception as e:
            print(f"Error generating report bundle: {e}")
            return pb2.GenerateReportBundleResponse(success=False, message=str(e))

    def GetSessions(self, request, context):
        request = request or pb2.GetSessionsRequest()
        cache, _ = self._load_user_data(context)
        data = cache.get("Session", [])
        meets = cache.get("Meet", [])
        meet_start = None
        if meets:
            m = meets[0]
            date_str = m.get("Start") or m.get("Start_date") or ""
            if date_str:
                try:
                    if " " in date_str:
                        date_str = date_str.split(" ")[0]
                    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d-%b-%y"):
                        try:
                            meet_start = datetime.datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

        # Count events per session from Sessitem for reliability
        sess_item_table = cache.get("Sessitem", []) or cache.get("SESSITEM", [])
        event_counts_map: dict[Any, int] = {}
        for si in sess_item_table:
            s_ptr = si.get("Sess_ptr")
            if s_ptr:
                event_counts_map[s_ptr] = event_counts_map.get(s_ptr, 0) + 1

        sessions_to_process = []
        if data:
            for item in data:
                s_ptr = item.get("Sess_ptr")
                e_cnt = self._safe_int(item.get("Event_cnt"))
                if not e_cnt and s_ptr:
                    e_cnt = event_counts_map.get(s_ptr, 0)

                sessions_to_process.append(
                    {
                        "id": str(item.get("Sess_no")),
                        "name": item.get("Sess_name", f"Session {item.get('Sess_no')}"),
                        "day": item.get("Sess_day", 1),
                        "warmup": item.get("Sess_warmup", 0),
                        "starttime": item.get("Sess_starttime", 0),
                        "event_cnt": e_cnt,
                        "source_item": item,
                    }
                )
        else:
            event_table = cache.get("Event", []) or cache.get("MTEVENT", [])
            sess_ids = sorted({self._safe_int(e.get("Sess_no", e.get("sess_no", 1))) for e in event_table})
            if not sess_ids and not event_table:
                sess_ids = [1]

            for s_id in sess_ids:
                sessions_to_process.append(
                    {
                        "id": str(s_id),
                        "name": "Session 1" if s_id == 1 and not event_table else f"Session {s_id}",
                        "day": 1,
                        "warmup": 0,
                        "starttime": 0,
                        "event_cnt": None,
                        "source_item": {},
                    }
                )

        sessions = []
        for s_info in sessions_to_process:
            item = s_info["source_item"]
            sess_date = ""
            day_offset = self._safe_int(s_info["day"], 1) - 1
            if meet_start and day_offset >= 0:
                s_date = meet_start + datetime.timedelta(days=day_offset)
                sess_date = s_date.strftime("%Y-%m-%d")
            else:
                sess_date = self._format_date(item.get("Sess_date", ""))

            s_no = s_info["id"]
            events = cache.get("Event", []) or cache.get("MTEVENT", [])
            ev_count = 0
            if s_no:
                ev_count = sum(1 for e in events if str(e.get("Sess_no", e.get("sess_no", 1))) == str(s_no))

            sessions.append(
                pb2.Session(
                    id=str(s_no),
                    meet_id="1",
                    name=s_info["name"],
                    date=sess_date,
                    warm_up_time=self._seconds_to_time(s_info["warmup"]),
                    start_time=self._seconds_to_time(s_info["starttime"]),
                    event_count=s_info.get("event_cnt") or ev_count,
                    session_num=self._safe_int(s_no, 0),
                    day=self._safe_int(s_info["day"], 1),
                )
            )
        return pb2.GetSessionsResponse(sessions=sessions)

    def GetAdminConfig(self, request, context):
        request = request or pb2.GetAdminConfigRequest()
        config = self._load_user_config(context)
        return pb2.GetAdminConfigResponse(
            meet_name=config.get("meet_name", ""), meet_description=config.get("meet_description", "")
        )

    def UpdateAdminConfig(self, request, context):
        request = request or pb2.UpdateAdminConfigRequest()
        self._check_auth(context)
        config = self._load_user_config(context)
        config["meet_name"] = request.meet_name
        config["meet_description"] = request.meet_description
        self._save_user_config(context, config)
        return pb2.UpdateAdminConfigResponse(
            meet_name=config.get("meet_name", ""), meet_description=config.get("meet_description", "")
        )

    def PublishMeetData(self, request, context):
        request = request or pb2.PublishMeetDataRequest()
        uid = self._check_auth(context)
        cache, config = self._load_user_data(context)
        current_file = config.get("active_dataset", SOURCE_FILE)

        try:
            from mm_to_json.judge_app_extractor import JudgeAppExtractor

            converter = MmToJsonConverter(table_data=cache)
            extractor = JudgeAppExtractor(converter)
            judge_data = extractor.extract_judge_data()

            # Save to a user-specific public-accessible location
            pub_dir = os.path.join(os.path.dirname(__file__), DATA_DIR, "published", uid)
            os.makedirs(pub_dir, exist_ok=True)

            filename = f"program_{current_file}.json"
            filepath = os.path.join(pub_dir, filename)
            with open(filepath, "w") as f:
                json.dump(judge_data, f)

            # Use uid in the program_url for isolation
            program_url = f"http://localhost:8080/data/published/{uid}/{filename}"
            base_url = "https://pfisherogden.github.io/MeetManager-Tools/judge"
            judge_app_url = f"{base_url}?program_url={program_url}"

            return pb2.PublishMeetDataResponse(success=True, message="Published", judge_app_url=judge_app_url)
        except Exception as e:
            print(f"Publish failed: {e}")
            return pb2.PublishMeetDataResponse(success=False, message=str(e))

    def _safe_int(self, value, default=0):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _seconds_to_time(self, seconds_val):
        try:
            val = int(seconds_val)
            hours = val // 3600
            minutes = (val % 3600) // 60
            period = "AM"
            if hours >= 12:
                period = "PM"
                if hours > 12:
                    hours -= 12
            if hours == 0:
                hours = 12
            return f"{hours}:{minutes:02d} {period}"
        except (ValueError, TypeError):
            return ""


def serve():
    port = os.getenv("PORT", "50051")
    interceptors = [FirebaseAuthInterceptor()]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors)

    # Add Health Servicer
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    pb2_grpc.add_MeetManagerServiceServicer_to_server(MeetManagerService(), server)

    server.add_insecure_port(f"[::]:{port}")
    print(f"Server starting on port {port} with AuthInterceptor and Health check...")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
