from concurrent import futures
import logging
import json
import os
import grpc

# Import generated classes
import meet_manager_pb2
import meet_manager_pb2_grpc
import csv
import subprocess
import io


# Defines where the source JSON data lives
DATA_DIR = "../data" 
SOURCE_FILE = "Sample_Data.json"
CONFIG_FILE = "config.json"

class MeetManagerService(meet_manager_pb2_grpc.MeetManagerServiceServicer):
    def __init__(self):
        self._data_cache = None
        self.current_file = SOURCE_FILE
        self._load_data()
        self._load_config()

    def _load_config(self):
        path = os.path.join(os.path.dirname(__file__), DATA_DIR, CONFIG_FILE)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = {"meet_name": "", "meet_description": ""}
        else:
             self.config = {"meet_name": "", "meet_description": ""}

    def _save_config(self):
        path = os.path.join(os.path.dirname(__file__), DATA_DIR, CONFIG_FILE)
        try:
            with open(path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _load_data(self):
        path = os.path.join(os.path.dirname(__file__), DATA_DIR, self.current_file)
        if not os.path.exists(path):
            print(f"Dataset not found at {path}")
            self._data_cache = {}
            return
        
        if self.current_file.endswith('.mdb'):
            print(f"Loading MDB dataset from {self.current_file}...")
            self._data_cache = self._load_mdb(path)
        else:
            with open(path, 'r') as f:
                self._data_cache = json.load(f)
            print(f"Loaded dataset from {SOURCE_FILE}. Keys: {list(self._data_cache.keys())}")

    def _load_mdb(self, path):
        """Parsing MDB using mdb-export commands."""
        cache = {}
        try:
            # Get tables
            tables_out = subprocess.check_output(["mdb-tables", "-1", path]).decode('utf-8')
            tables = tables_out.strip().split()
            
            for table in tables:
                # Export as CSV
                csv_out = subprocess.check_output(["mdb-export", path, table]).decode('utf-8')
                # Parse CSV
                reader = csv.DictReader(io.StringIO(csv_out))
                rows = list(reader)
                cache[table] = rows
                # Also store as mixed case if needed or rely on fuzzy matching in getters
            
            print(f"Loaded {len(tables)} tables from MDB.")
            return cache
        except Exception as e:
            print(f"Error loading MDB: {e}")
            return {}

    def UploadDataset(self, request_iterator, context):
        print("DEBUG: UploadDataset called", flush=True)
        filename = "uploaded.mdb" 
        filepath = os.path.join(os.path.dirname(__file__), DATA_DIR, filename)
        
        # Temporary buffer to hold file content while we wait for filename
        file_content = io.BytesIO()
        
        try:
            for request in request_iterator:
                if request.HasField("filename"):
                    filename = request.filename
                    safe_name = os.path.basename(filename)
                    # Security check: Ensure .mdb extension
                    if not safe_name.lower().endswith('.mdb'):
                         safe_name += ".mdb"
                    
                    filename = safe_name
                    filepath = os.path.join(os.path.dirname(__file__), DATA_DIR, filename)
                
                if request.HasField("chunk"):
                    file_content.write(request.chunk)
            
            # Now write the buffer to the actual file
            with open(filepath, 'wb') as f:
                f.write(file_content.getvalue())

            print(f"Saved uploaded file to {filepath}")
            
            # CRITICAL FIX: Reload the data immediately if we overwrote the current file
            # or if we want to switch to it. 
            # Ideally we check if self.current_file matches, but usually user wants to see it now.
            # So let's force a reload if it's the active file, or just invoke loading.
            if filename == self.current_file:
                print(f"Reloading active dataset {filename}...")
                self._load_data()
            else:
                # Optional: Auto-switch? Let's just reload if it is the current file.
                # If it's a new file, the user might need to 'SetActiveDataset' via UI.
                # But if they uploaded 'uploaded.mdb' and we are using 'uploaded.mdb', reload!
                pass

            return meet_manager_pb2.UploadResponse(success=True, message=f"Saved {filename}")
        except Exception as e:
            print(f"Upload failed: {e}")
            return meet_manager_pb2.UploadResponse(success=False, message=str(e))


    def _get_table(self, table_name):
        return self._data_cache.get(table_name, [])

    def GetDashboardStats(self, request, context):
        teams = self._get_table('Team')
        athletes = self._get_table('Athlete')
        events = self._get_table('Event')
        meets = self._get_table('Meet')
        
        return meet_manager_pb2.DashboardStats(
            meet_count=len(meets),
            team_count=len(teams),
            athlete_count=len(athletes),
            event_count=len(events)
        )

    def GetMeets(self, request, context):
        data = self._get_table('Meet')
        meets = []
        for item in data:
            name = item.get('Meet_name') or item.get('MName') or 'Unknown Meet'
            loc = item.get('Location') or item.get('Meet_location') or ''
            start = str(item.get('Start_date') or item.get('Start') or '')
            end = str(item.get('End_date') or item.get('End') or '')
            
            meets.append(meet_manager_pb2.Meet(
                id="1", 
                name=name, 
                location=loc,
                start_date=start,
                end_date=end,
                status="active"
            ))
        return meet_manager_pb2.MeetList(meets=meets)

    def GetTeams(self, request, context):
        data = self._get_table('Team')
        athletes = self._get_table('Athlete')
        
        # Count athletes per team
        ath_counts = {}
        for ath in athletes:
            t_id = int(ath.get('Team_no', 0))
            ath_counts[t_id] = ath_counts.get(t_id, 0) + 1

        teams = []
        for item in data:
            t_id = int(item.get('Team_no', 0))
            teams.append(meet_manager_pb2.Team(
                id=t_id,
                name=item.get('Team_name', 'Unknown'),
                code=item.get('Team_abbr', ''),
                lsc=item.get('Team_lsc', ''),
                city=item.get('Team_city', ''),
                state=item.get('Team_statenew', ''),
                athlete_count=ath_counts.get(t_id, 0)
            ))
        return meet_manager_pb2.TeamList(teams=teams)

    def GetTeam(self, request, context):
        team_id = request.id
        data = self._get_table('Team')
        for item in data:
            if int(item.get('Team_no', 0)) == team_id:
                return meet_manager_pb2.Team(
                    id=int(item.get('Team_no', 0)),
                    name=item.get('Team_name', 'Unknown'),
                    code=item.get('Team_abbr', ''),
                    lsc=item.get('Team_lsc', ''),
                    city=item.get('Team_city', ''),
                    state=item.get('Team_statenew', ''),
                    athlete_count=0 
                )
        
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Team {team_id} not found")
        return meet_manager_pb2.Team()

    def GetAthletes(self, request, context):
        data = self._get_table('Athlete')
        # We need to map Team ID to Name for efficient display, or join manually
        teams_map = {int(t.get('Team_no', 0)): t.get('Team_name') for t in self._get_table('Team')}
        
        athletes = []
        for item in data:
            t_id = int(item.get('Team_no', 0))
            athletes.append(meet_manager_pb2.Athlete(
                id=int(item.get('Ath_no', 0)),
                first_name=item.get('First_name', ''),
                last_name=item.get('Last_name', ''),
                gender=item.get('Ath_Sex', ''),
                age=int(item.get('Ath_age', 0)),
                team_id=t_id,
                team_name=teams_map.get(t_id, 'Unknown'), 
                school_year=item.get('School_yr', ''),
                reg_no=item.get('Reg_no', '')
            ))
        return meet_manager_pb2.AthleteList(athletes=athletes)

    def GetAthlete(self, request, context):
        ath_id = request.id
        data = self._get_table('Athlete')
        teams_map = {int(t.get('Team_no', 0)): t.get('Team_name') for t in self._get_table('Team')}
        
        for item in data:
            if int(item.get('Ath_no', 0)) == ath_id:
                t_id = int(item.get('Team_no', 0))
                return meet_manager_pb2.Athlete(
                    id=int(item.get('Ath_no', 0)),
                    first_name=item.get('First_name', ''),
                    last_name=item.get('Last_name', ''),
                    gender=item.get('Ath_Sex', ''),
                    age=int(item.get('Ath_age', 0)),
                    team_id=t_id,
                    team_name=teams_map.get(t_id, 'Unknown'), 
                    school_year=item.get('School_yr', ''),
                    reg_no=item.get('Reg_no', '')
                )
        
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Athlete {ath_id} not found")
        return meet_manager_pb2.Athlete()

    def GetEvents(self, request, context):
        data = self._get_table('Event')
        events = []
        stroke_map = {
            'A': 'Freestyle',
            'B': 'Backstroke',
            'C': 'Breaststroke',
            'D': 'Butterfly',
            'E': 'IM' 
        }
        gender_map = {
            'B': 'Boys',
            'G': 'Girls',
            'X': 'Mixed',
            'M': 'Men',
            'F': 'Women',
            'W': 'Women'
        }

        for item in data:
            # Stroke mapping
            raw_stroke = item.get('Event_stroke', '').upper().strip()
            stroke_desc = stroke_map.get(raw_stroke, raw_stroke)
            
            # Refine IM vs Medley based on Ind_rel
            is_relay = (item.get('Ind_rel', '').upper().strip() == 'R')
            if raw_stroke == 'E' and is_relay:
                stroke_desc = "Medley Relay"
            elif is_relay and stroke_desc != raw_stroke:
                 stroke_desc += " Relay"

            # Gender mapping
            raw_gender = item.get('Event_sex', '').upper().strip()
            gender_desc = gender_map.get(raw_gender, raw_gender)

            events.append(meet_manager_pb2.Event(
                id=int(item.get('Event_no', 0)),
                gender=gender_desc,
                distance=int(item.get('Event_dist', 0)),
                stroke=stroke_desc,
                low_age=int(item.get('Low_age', 0)),
                high_age=int(item.get('High_Age', 0))
            ))
        return meet_manager_pb2.EventList(events=events)

    def ListDatasets(self, request, context):
        """Scans the data directory for .json files."""
        datasets = []
        data_dir = os.path.join(os.path.dirname(__file__), DATA_DIR)
        print(f"DEBUG: ListDatasets scanning {data_dir}", flush=True)
        try:
            files = os.listdir(data_dir)
            print(f"DEBUG: Found files: {files}", flush=True)
            for filename in files:
                if filename.endswith(".json") or filename.endswith(".mdb"):
                    full_path = os.path.join(data_dir, filename)
                    # Simple metadata (try/except for race conditions)
                    try:
                        mod_time = os.path.getmtime(full_path)
                    except OSError:
                        mod_time = 0
                    
                    is_active = (filename == self.current_file)
                    
                    datasets.append(meet_manager_pb2.Dataset(
                        filename=filename,
                        is_active=is_active,
                        last_modified=str(mod_time)
                    ))
        except Exception as e:
            print(f"Error listing datasets: {e}")
            
        return meet_manager_pb2.DatasetList(datasets=datasets)

    def SetActiveDataset(self, request, context):
        """Switches the active dataset file and reloads cache."""
        filename = request.filename
        path = os.path.join(os.path.dirname(__file__), DATA_DIR, filename)
        
        if not os.path.exists(path):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"File {filename} not found.")
            return meet_manager_pb2.Empty()

        print(f"Switching dataset to {filename}...")
        self.current_file = filename
        self._load_data()
        return meet_manager_pb2.Empty()

    # ... existing methods ...

    def _safe_int(self, value, default=0):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def GetRelays(self, request, context):
        """Fetches Relay entries, joining with Team data."""
        relays_data = self._get_table('RELAY')  # Assuming table name is capital RELAY
        if not relays_data:
             relays_data = self._get_table('Relay') # Try mixed case
        
        teams = {t.get('Team_no'): t.get('Team_name') for t in self._get_table('Team')}
        
        result = []
        for idx, item in enumerate(relays_data):
            t_id = item.get('Team_ptr', 0)
            if not t_id:
                t_id = item.get('Team_no', 0)
            
            result.append(meet_manager_pb2.Relay(
                id=idx, 
                event_id=self._safe_int(item.get('Event_ptr')),
                team_id=self._safe_int(t_id),
                team_name=teams.get(t_id, 'Unknown'),
                leg1_name="", 
                leg2_name="",
                leg3_name="",
                leg4_name="",
                seed_time=str(item.get('Seed_Time', 'NT')),
                final_time=str(item.get('Finals_Time', '')),
                place=self._safe_int(item.get('Place'))
            ))
        return meet_manager_pb2.RelayList(relays=result)

    def GetScores(self, request, context):
        """Fetches or calculates team scores."""
        scores_data = self._get_table('TEAMSCOR') 
        teams = {t.get('Team_no'): t for t in self._get_table('Team')}
        
        result = []
        if scores_data:
            for item in scores_data:
                 t_id = item.get('Team_no')
                 result.append(meet_manager_pb2.Score(
                     team_id=self._safe_int(t_id),
                     team_name=teams.get(t_id, {}).get('Team_name', 'Unknown'),
                     individual_points=self._safe_float(item.get('Ind_score')),
                     relay_points=self._safe_float(item.get('Rel_score')),
                     total_points=self._safe_float(item.get('Tot_score')),
                     rank=self._safe_int(item.get('Place'))
                 ))
        else:
             for t_id, team in teams.items():
                 result.append(meet_manager_pb2.Score(
                     team_id=self._safe_int(t_id),
                     team_name=team.get('Team_name', 'Unknown'),
                     individual_points=0,
                     relay_points=0,
                     total_points=0,
                     rank=0
                 ))
        
        return meet_manager_pb2.ScoreList(scores=result)

    def GetEntries(self, request, context):
        """Fetches individual entries."""
        entries_data = self._get_table('Entry') # or ENTRY
        if not entries_data:
            entries_data = self._get_table('ENTRY')
        
        athletes = {a.get('Ath_no'): a for a in self._get_table('Athlete')}
        teams = {t.get('Team_no'): t.get('Team_name') for t in self._get_table('Team')}
        
        result = []
        for idx, item in enumerate(entries_data):
            ath_id = item.get('Ath_no', 0)
            athlete = athletes.get(ath_id, {})
            t_id = athlete.get('Team_no', 0)
            
            result.append(meet_manager_pb2.Entry(
                id=idx, 
                event_id=self._safe_int(item.get('Event_ptr')),
                athlete_id=self._safe_int(ath_id),
                athlete_name=f"{athlete.get('First_name','')} {athlete.get('Last_name','')}",
                team_id=self._safe_int(t_id),
                team_name=teams.get(t_id, 'Unknown'),
                seed_time=str(item.get('Seed_Time', 'NT')),
                final_time=str(item.get('Finals_Time', '')),
                place=self._safe_int(item.get('Place'))
            ))
        return meet_manager_pb2.EntryList(entries=result)

    def GetSessions(self, request, context):
        # Trying to find explicit sessions table first (often 'Session' or derived from Events)
        # Assuming we might not have a Session table, we can infer from Events session column.
        
        # NOTE: MDBTools may not export Session table if we didn't ask for it, 
        # but _load_mdb loads ALL tables.
        
        sessions_data = self._get_table('Session') 
        if not sessions_data:
             sessions_data = self._get_table('SESSION')
        
        events = self._get_table('Event')
        
        final_sessions = []
        
        if sessions_data:
            for item in sessions_data:
                 # Check event count for this session
                 sess_no = int(item.get('Sess_no', 0))
                 sess_events = [e for e in events if int(e.get('Sess_no', 0) if e.get('Sess_no') else 0) == sess_no]
                 
                 final_sessions.append(meet_manager_pb2.Session(
                     id=str(item.get('Sess_no', '')),
                     meet_id="1", 
                     name=item.get('Sess_name', f"Session {sess_no}"),
                     date=str(item.get('Sess_date', '')), # formatting needed?
                     warm_up_time=str(item.get('Sess_time', '')), # Field names vary
                     start_time=str(item.get('Sess_starttime', '')),
                     event_count=len(sess_events),
                     session_num=sess_no,
                     day=int(item.get('Sess_day', 0))
                 ))
        
        # If no session data found or empty, infer from events or return default
        if not final_sessions:
            if events:
                 # Group by Sess_no
                 sessions_map = {}
                 for e in events:
                     s_no = int(e.get('Sess_no', 0) if e.get('Sess_no') else 1) # Default to 1 if missing
                     if s_no not in sessions_map:
                         sessions_map[s_no] = 0
                     sessions_map[s_no] += 1
                 
                 for s_no, count in sessions_map.items():
                     final_sessions.append(meet_manager_pb2.Session(
                         id=str(s_no),
                         meet_id="1",
                         name=f"Session {s_no}",
                         event_count=count,
                         session_num=s_no,
                         day=1, # Default
                         start_time="00:00 AM" 
                     ))
            else:
                 # Absolutely no data
                 final_sessions.append(meet_manager_pb2.Session(
                     id="0",
                     meet_id="1",
                     name="All Events",
                     event_count=0,
                     session_num=0
                 ))
                 
        return meet_manager_pb2.SessionList(sessions=final_sessions)

    def GetAdminConfig(self, request, context):
        return meet_manager_pb2.AdminConfig(
            meet_name=self.config.get('meet_name', ''),
            meet_description=self.config.get('meet_description', '')
        )

    def UpdateAdminConfig(self, request, context):
        self.config['meet_name'] = request.meet_name
        self.config['meet_description'] = request.meet_description
        self._save_config()
        return self.GetAdminConfig(request, context)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    meet_manager_pb2_grpc.add_MeetManagerServiceServicer_to_server(MeetManagerService(), server)
    server.add_insecure_port('[::]:50051')
    print("Server started on port 50051")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig()
    serve()
