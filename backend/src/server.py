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

class MeetManagerService(meet_manager_pb2_grpc.MeetManagerServiceServicer):
    def __init__(self):
        self._data_cache = None
        self.current_file = SOURCE_FILE
        self._load_data()

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
        
        try:
            with open(filepath, 'wb') as f:
                for request in request_iterator:
                    if request.HasField("filename"):
                        filename = request.filename
                        # Update path with real filename if sent first, 
                        # but careful about directory traversal paths.
                        safe_name = os.path.basename(filename)
                        filepath = os.path.join(os.path.dirname(__file__), DATA_DIR, safe_name)
                    
                    if request.HasField("chunk"):
                        f.write(request.chunk)
            
            print(f"Saved uploaded file to {filepath}")
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
        teams = []
        for item in data:
            teams.append(meet_manager_pb2.Team(
                id=item.get('Team_no', 0),
                name=item.get('Team_name', 'Unknown'),
                code=item.get('Team_abbr', ''),
                lsc=item.get('Team_lsc', ''),
                city=item.get('Team_city', ''),
                state=item.get('Team_statenew', ''),
                athlete_count=0 
            ))
        return meet_manager_pb2.TeamList(teams=teams)

    def GetAthletes(self, request, context):
        data = self._get_table('Athlete')
        # We need to map Team ID to Name for efficient display, or join manually
        teams_map = {t.get('Team_no'): t.get('Team_name') for t in self._get_table('Team')}
        
        athletes = []
        for item in data:
            t_id = item.get('Team_no', 0)
            athletes.append(meet_manager_pb2.Athlete(
                id=item.get('Ath_no', 0),
                first_name=item.get('First_name', ''),
                last_name=item.get('Last_name', ''),
                gender=item.get('Ath_Sex', ''),
                age=item.get('Ath_age', 0),
                team_id=t_id,
                team_name=teams_map.get(t_id, 'Unknown'), 
                school_year=item.get('School_yr', ''),
                reg_no=item.get('Reg_no', '')
            ))
        return meet_manager_pb2.AthleteList(athletes=athletes)

    def GetEvents(self, request, context):
        data = self._get_table('Event')
        events = []
        for item in data:
            events.append(meet_manager_pb2.Event(
                id=int(item.get('Event_no', 0)),
                gender=item.get('Event_sex', ''),
                distance=int(item.get('Event_dist', 0)),
                stroke=item.get('Event_stroke', ''),
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

    def GetRelays(self, request, context):
        """Fetches Relay entries, joining with Team data."""
        relays_data = self._get_table('RELAY')  # Assuming table name is capital RELAY
        if not relays_data:
             relays_data = self._get_table('Relay') # Try mixed case

        teams = {t.get('Team_no'): t.get('Team_name') for t in self._get_table('Team')}
        # Athletes map for names? Usually relays have Ath_no_1, etc.
        # For now, simplest implementation: just return raw data if names aren't simple FKs
        
        result = []
        for idx, item in enumerate(relays_data):
            t_id = item.get('Team_ptr', 0) # Meet Manager often uses Team_ptr or Team_no
            if not t_id:
                t_id = item.get('Team_no', 0)
            
            result.append(meet_manager_pb2.Relay(
                id=idx, # Or item.get('Relay_no')
                event_id=item.get('Event_ptr', 0),
                team_id=t_id,
                team_name=teams.get(t_id, 'Unknown'),
                # Names might be separate columns or linked. Placeholder for now.
                leg1_name="", 
                leg2_name="",
                leg3_name="",
                leg4_name="",
                seed_time=str(item.get('Seed_Time', 'NT')),
                final_time=str(item.get('Finals_Time', '')),
                place=int(item.get('Place', 0) or 0)
            ))
        return meet_manager_pb2.RelayList(relays=result)

    def GetScores(self, request, context):
        """Fetches or calculates team scores."""
        # Check if score table exists (e.g. TEAMSCOR)
        scores_data = self._get_table('TEAMSCOR') 
        teams = {t.get('Team_no'): t for t in self._get_table('Team')}
        
        result = []
        if scores_data:
            for item in scores_data:
                 t_id = item.get('Team_no')
                 result.append(meet_manager_pb2.Score(
                     team_id=t_id,
                     team_name=teams.get(t_id, {}).get('Team_name', 'Unknown'),
                     individual_points=float(item.get('Ind_score', 0)),
                     relay_points=float(item.get('Rel_score', 0)),
                     total_points=float(item.get('Tot_score', 0)),
                     rank=int(item.get('Place', 0) or 0)
                 ))
        else:
             # Calculate simple score based on entries? Too complex for now.
             # Return dummy score based on team list just to show something
             for t_id, team in teams.items():
                 result.append(meet_manager_pb2.Score(
                     team_id=t_id,
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
                id=idx, # Entry usually has no ID, it's a link table
                event_id=item.get('Event_ptr', 0),
                athlete_id=ath_id,
                athlete_name=f"{athlete.get('First_name','')} {athlete.get('Last_name','')}",
                team_id=t_id,
                team_name=teams.get(t_id, 'Unknown'),
                seed_time=str(item.get('Seed_Time', 'NT')),
                final_time=str(item.get('Finals_Time', '')),
                place=int(item.get('Place', 0) or 0)
            ))
        return meet_manager_pb2.EntryList(entries=result)

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
