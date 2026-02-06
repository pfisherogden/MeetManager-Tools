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
        
    def GetAthletes(self, request, context):
        data = self._get_table('Athlete')
        # We need to map Team ID to Name for efficient display, or join manually
        teams_map = {int(t.get('Team_no', 0)): t.get('Team_name') for t in self._get_table('Team')}
        
        athletes = []
        for item in data:
            t_id = int(item.get('Team_no', 0))
            # Birthdate parsing: "01/28/11 00:00:00"
            dob_raw = item.get('Ath_birthdate') or item.get('Birth_date') or ''
            dob = dob_raw.split(' ')[0] if dob_raw else ''

            athletes.append(meet_manager_pb2.Athlete(
                id=int(item.get('Ath_no', 0)),
                first_name=item.get('First_name', ''),
                last_name=item.get('Last_name', ''),
                gender=item.get('Ath_Sex', ''),
                age=int(item.get('Ath_age', 0)),
                team_id=t_id,
                team_name=teams_map.get(t_id, 'Unknown'), 
                school_year=item.get('School_yr', ''),
                reg_no=item.get('Reg_no', ''),
                date_of_birth=dob
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

    def _seconds_to_time(self, seconds_val):
        """Converts raw integer seconds (or similar) to HH:MM AM/PM."""
        try:
            val = int(seconds_val)
            # Assuming seconds from midnight
            hours = val // 3600
            minutes = (val % 3600) // 60
            # AM/PM
            period = "AM"
            if hours >= 12:
                period = "PM"
                if hours > 12:
                    hours -= 12
            if hours == 0:
                hours = 12
            if hours == 12 and period == "AM": # Midnight case?
                 pass
            return f"{hours}:{minutes:02d} {period}"
        except (ValueError, TypeError):
            return ""

    def GetRelays(self, request, context):
        """Fetches Relay entries, joining with Team data."""
        relays_data = self._get_table('Relay')  # Assuming table name is capital RELAY
        if not relays_data:
             relays_data = self._get_table('RELAY') # Try mixed case
        
        # Load RelayNames to get swimmers
        relay_names_data = self._get_table('RelayNames')
        # Index RelayNames by (Event_ptr, Team_no, Relay_no)
        relay_legs_map = {}
        for rn in relay_names_data:
            key = (rn.get('Event_ptr'), rn.get('Team_no'), rn.get('Relay_no'))
            if key not in relay_legs_map:
                relay_legs_map[key] = []
            relay_legs_map[key].append(rn)
        
        teams = {t.get('Team_no'): t.get('Team_name') for t in self._get_table('Team')}
        athletes = {a.get('Ath_no'): a for a in self._get_table('Athlete')}
        
        # Pre-process Events mapping
        events_map = {}
        stroke_map = {'A': 'Free', 'B': 'Back', 'C': 'Breast', 'D': 'Fly', 'E': 'IM'}
        gender_map = {'B': 'Boys', 'G': 'Girls', 'X': 'Mixed', 'M': 'Men', 'W': 'Women', 'F': 'Women'}
        
        for e in self._get_table('Event'):
             e_no = e.get('Event_no') or e.get('Event_ptr')
             if e_no:
                  g = gender_map.get(e.get('Event_sex','').strip(), e.get('Event_sex',''))
                  d = e.get('Event_dist','')
                  s = stroke_map.get(e.get('Event_stroke','').strip(), e.get('Event_stroke',''))
                  low = e.get('Low_age','')
                  high = e.get('High_Age','')
                  name = f"{g} {low}-{high} {d} {s}"
                  events_map[e_no] = name

        result = []
        for idx, item in enumerate(relays_data):
            t_id = item.get('Team_ptr', 0)
            if not t_id or t_id == '0':
                t_id = item.get('Team_no', 0)
            
            event_ptr = item.get('Event_ptr')
            relay_no = item.get('Relay_no')
            
            # Find legs
            legs = relay_legs_map.get((event_ptr, t_id, relay_no), [])
            # Sort by Pos_no
            legs.sort(key=lambda x: int(x.get('Pos_no', 0) if x.get('Pos_no') and x.get('Pos_no').strip().isdigit() else 99))
            
            leg_names = ["", "", "", ""]
            for leg in legs:
                try:
                    pos = int(leg.get('Pos_no', 0))
                    if 1 <= pos <= 4:
                        ath_id = leg.get('Ath_no')
                        ath = athletes.get(ath_id)
                        if ath:
                            leg_names[pos-1] = f"{ath.get('First_name','')} {ath.get('Last_name','')}"
                except ValueError:
                    continue

            # Fix Seed Time (NT if empty or 0)
            seed = item.get('ActualSeed_time') or item.get('ConvSeed_time') or item.get('Seed_Time') or 'NT'
            try:
                 if float(seed) == 0: seed = 'NT'
            except:
                 pass

            result.append(meet_manager_pb2.Relay(
                id=idx, 
                event_id=self._safe_int(item.get('Event_ptr')),
                team_id=self._safe_int(t_id),
                team_name=teams.get(t_id, 'Unknown'),
                leg1_name=leg_names[0], 
                leg2_name=leg_names[1],
                leg3_name=leg_names[2],
                leg4_name=leg_names[3],
                seed_time=str(seed),
                final_time=str(item.get('Fin_Time', '')),
                place=self._safe_int(item.get('Fin_place', item.get('Place'))),
                event_name=events_map.get(event_ptr, f"Event {event_ptr}"),
                relay_letter=item.get('Team_ltr', '')
            ))
        return meet_manager_pb2.RelayList(relays=result)

    def GetScores(self, request, context):
        """Fetches or calculates team scores."""
        # Calculate from Entry and Relay Ev_score
        teams = {t.get('Team_no'): {'name': t.get('Team_name'), 'id': t.get('Team_no')} for t in self._get_table('Team')}
        scores = {t_id: {'ind': 0.0, 'rel': 0.0} for t_id in teams}
        
        # Process Entries
        entries_data = self._get_table('Entry') or self._get_table('ENTRY')
        athletes = {a.get('Ath_no'): a for a in self._get_table('Athlete')}
        
        if entries_data:
            for e in entries_data:
                 ath_id = e.get('Ath_no')
                 ath = athletes.get(ath_id)
                 if ath:
                      t_id = ath.get('Team_no')
                      if t_id in scores:
                           val = self._safe_float(e.get('Ev_score', 0))
                           scores[t_id]['ind'] += val

        # Process Relays
        relays_data = self._get_table('Relay') or self._get_table('RELAY')
        if relays_data:
            for r in relays_data:
                 t_id = r.get('Team_no') # Or Team_ptr
                 if not t_id or t_id == '0':
                      t_id = r.get('Team_ptr')
                 
                 if t_id in scores:
                      val = self._safe_float(r.get('Ev_score', 0))
                      scores[t_id]['rel'] += val

        result = []
        for t_id, s in scores.items():
             total = s['ind'] + s['rel']
             result.append(meet_manager_pb2.Score(
                 team_id=self._safe_int(t_id),
                 team_name=teams[t_id]['name'],
                 individual_points=s['ind'],
                 relay_points=s['rel'],
                 total_points=total,
                 rank=0 
             ))
        
        # Sort by total points desc
        result.sort(key=lambda x: x.total_points, reverse=True)
        for i, r in enumerate(result):
             if r.total_points > 0:
                 r.rank = i + 1
        
        return meet_manager_pb2.ScoreList(scores=result)

    def GetEntries(self, request, context):
        """Fetches individual entries."""
        entries_data = self._get_table('Entry') # or ENTRY
        if not entries_data:
            entries_data = self._get_table('ENTRY')
        
        athletes = {a.get('Ath_no'): a for a in self._get_table('Athlete')}
        teams = {t.get('Team_no'): t.get('Team_name') for t in self._get_table('Team')}
        # Pre-process Events mapping
        events_map = {}
        stroke_map = {'A': 'Free', 'B': 'Back', 'C': 'Breast', 'D': 'Fly', 'E': 'IM'}
        gender_map = {'B': 'Boys', 'G': 'Girls', 'X': 'Mixed', 'M': 'Men', 'W': 'Women', 'F': 'Women'}
        
        for e in self._get_table('Event'):
             e_no = e.get('Event_no') or e.get('Event_ptr')
             if e_no:
                  g = gender_map.get(e.get('Event_sex','').strip(), e.get('Event_sex',''))
                  d = e.get('Event_dist','')
                  s = stroke_map.get(e.get('Event_stroke','').strip(), e.get('Event_stroke',''))
                  low = e.get('Low_age','')
                  high = e.get('High_Age','')
                  name = f"{g} {low}-{high} {d} {s}"
                  events_map[e_no] = name

        result = []
        for idx, item in enumerate(entries_data):
            ath_id = item.get('Ath_no', 0)
            athlete = athletes.get(ath_id, {})
            t_id = athlete.get('Team_no', 0)
            event_id = item.get('Event_ptr')

            seed = item.get('ActualSeed_time') or item.get('ConvSeed_time') or item.get('Seed_Time') or 'NT'
            try:
                 if float(seed) == 0: seed = 'NT'
            except:
                 pass

            result.append(meet_manager_pb2.Entry(
                id=idx, 
                event_id=self._safe_int(event_id),
                athlete_id=self._safe_int(ath_id),
                athlete_name=f"{athlete.get('First_name','')} {athlete.get('Last_name','')}",
                team_id=self._safe_int(t_id),
                team_name=teams.get(t_id, 'Unknown'),
                seed_time=str(seed),
                final_time=str(item.get('Fin_Time', '')),
                place=self._safe_int(item.get('Fin_place', item.get('Place'))),
                event_name=events_map.get(event_id, f"Event {event_id}"),
                heat=self._safe_int(item.get('Fin_heat', item.get('Pre_heat', 0))),
                lane=self._safe_int(item.get('Fin_lane', item.get('Pre_lane', 0))),
                points=self._safe_float(item.get('Ev_score', 0.0))
            ))
        return meet_manager_pb2.EntryList(entries=result)

    def GetEventScores(self, request, context):
        """Fetches detailed scores per event (Entries and Relays)."""
        # Load all needed data
        entries = self._get_table('Entry') or self._get_table('ENTRY')
        relays = self._get_table('Relay') or self._get_table('RELAY')
        athletes_map = {a.get('Ath_no'): a for a in self._get_table('Athlete')}
        teams_map = {t.get('Team_no'): t.get('Team_name') for t in self._get_table('Team')}
        
        # Build Event Map
        events_map = {}
        stroke_map = {'A': 'Free', 'B': 'Back', 'C': 'Breast', 'D': 'Fly', 'E': 'IM'}
        gender_map = {'B': 'Boys', 'G': 'Girls', 'X': 'Mixed', 'M': 'Men', 'W': 'Women', 'F': 'Women'}
        
        # Events by ID
        event_dict = {}
        
        for e in self._get_table('Event'):
             e_no = e.get('Event_no') or e.get('Event_ptr')
             if not e_no: continue
             
             g = gender_map.get(e.get('Event_sex','').strip(), e.get('Event_sex',''))
             d = e.get('Event_dist','')
             s_raw = e.get('Event_stroke','').strip()
             s = stroke_map.get(s_raw, s_raw)
             
             # Relay check
             is_relay = (e.get('Ind_rel', '').upper().strip() == 'R')
             if s_raw == 'E' and is_relay: s = "Medley Relay"
             elif is_relay and s != s_raw: s += " Relay"
             
             low = e.get('Low_age','')
             high = e.get('High_Age','')
             name = f"{g} {low}-{high} {d} {s}"
             events_map[e_no] = name
             event_dict[e_no] = {'id': int(e_no), 'name': name, 'entries': []}

        # Process Individual Entries
        for item in entries:
             e_id = item.get('Event_ptr')
             if e_id not in event_dict:
                  continue
             
             ath_id = item.get('Ath_no')
             ath = athletes_map.get(ath_id)
             t_id = ath.get('Team_no', 0) if ath else 0
             
             # Check if it has a score or place
             place = self._safe_int(item.get('Fin_place', item.get('Place', 0)))
             points = self._safe_float(item.get('Ev_score', 0))
             
             # Only include scored items or finalists? User asked for "scores for each event, including athletes and ranks"
             # So maybe just list everyone who participated? 
             # Let's list everyone who has a place or score.
             
             entry_obj = meet_manager_pb2.Entry(
                 id=0, # Not vital here
                 event_id=int(e_id),
                 athlete_id=int(ath_id if ath else 0),
                 athlete_name=f"{ath.get('First_name','')} {ath.get('Last_name','')}" if ath else "Unknown",
                 team_id=int(t_id),
                 team_name=teams_map.get(t_id, 'Unknown'),
                 final_time=str(item.get('Fin_Time', '')),
                 place=place,
                 event_name=events_map.get(e_id, "")
             )
             event_dict[e_id]['entries'].append(entry_obj)

        # Process Relays
        for item in relays:
             e_id = item.get('Event_ptr')
             if e_id not in event_dict:
                  continue
                  
             t_id = item.get('Team_ptr') or item.get('Team_no')
             place = self._safe_int(item.get('Fin_place', item.get('Place', 0)))
             
             # Create a "pseudo-entry" for the relay team
             entry_obj = meet_manager_pb2.Entry(
                 id=0,
                 event_id=int(e_id),
                 athlete_id=0,
                 athlete_name="Relay Team", # Or list legs?
                 team_id=int(t_id if t_id else 0),
                 team_name=teams_map.get(t_id, 'Unknown'),
                 final_time=str(item.get('Fin_Time', '')),
                 place=place,
                 event_name=events_map.get(e_id, "")
             )
             event_dict[e_id]['entries'].append(entry_obj)

        # Build response
        resp_list = []
        # Sort events by ID
        sorted_keys = sorted(event_dict.keys(), key=lambda k: int(k))
        for k in sorted_keys:
             ev = event_dict[k]
             # Sort entries by place
             ev['entries'].sort(key=lambda x: x.place if x.place > 0 else 9999)
             
             resp_list.append(meet_manager_pb2.EventScore(
                 event_id=ev['id'],
                 event_name=ev['name'],
                 entries=ev['entries']
             ))
             
        return meet_manager_pb2.EventScoreList(event_scores=resp_list)

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
                     warm_up_time=self._seconds_to_time(item.get('Sess_time', '')), 
                     start_time=self._seconds_to_time(item.get('Sess_starttime', '')),
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
