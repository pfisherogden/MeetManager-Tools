from concurrent import futures
import logging
import json
import os
import grpc
import datetime

# Import generated classes
import meet_manager_pb2
import meet_manager_pb2_grpc
import csv
import subprocess
import io
import tempfile
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.report_generator import ReportGenerator


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
            loc = item.get('Location') or item.get('Meet_location') or ''
            start = self._format_date(item.get('Start') or item.get('Start_date') or '')
            end = self._format_date(item.get('End') or item.get('End_date') or '')
            
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

        # Pre-calculate entry counts per event
        entry_counts = {}
        entries = self._get_table('Entry') or self._get_table('ENTRY')
        for e in entries:
             evt_ptr = e.get('Event_ptr')
             if evt_ptr:
                  entry_counts[evt_ptr] = entry_counts.get(evt_ptr, 0) + 1

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
                high_age=int(item.get('High_Age', 0)),
                entry_count=entry_counts.get(item.get('Event_no') or item.get('Event_ptr'), 0)
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

    def _format_date(self, date_str):
        """Standardizes date strings to YYYY-MM-DD."""
        if not date_str:
            return ""
        try:
            # Check if already in YYYY-MM-DD
            # Simple heuristic
            date_str = str(date_str).strip()
            if " " in date_str:
                date_str = date_str.split(" ")[0]
            
            # Common formats
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%y"):
                try:
                    dt = datetime.datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return date_str # Return original if parse fails
        except Exception:
            return str(date_str)


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
                relay_letter=item.get('Team_ltr', ''),
                heat=self._safe_int(item.get('Fin_heat')),
                lane=self._safe_int(item.get('Fin_lane'))
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
        events_sex_map = {e.get('Event_no') or e.get('Event_ptr'): e.get('Event_sex', 'M') for e in self._get_table('Event')}
        
        if entries_data:
            for e in entries_data:
                 ath_id = e.get('Ath_no')
                 # Use athletes from line 483
                 ath = athletes.get(ath_id)
                 if ath:
                      t_id = ath.get('Team_no')
                      if t_id in scores:
                           e_id = e.get('Event_ptr')
                           sex = events_sex_map.get(e_id, ath.get('Ath_Sex', 'M'))
                           val = self._calculate_points(e, sex, False)
                           scores[t_id]['ind'] += val

        # Process Relays
        relays_data = self._get_table('Relay') or self._get_table('RELAY')
        if relays_data:
            for r in relays_data:
                 t_id = r.get('Team_no') # Or Team_ptr
                 if not t_id or t_id == '0':
                      t_id = r.get('Team_ptr')
                 
                 if t_id in scores:
                      e_id = r.get('Event_ptr')
                      sex = events_sex_map.get(e_id, r.get('Rel_sex', 'X'))
                      val = self._calculate_points(r, sex, True)
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
                 rank=0,

                 meet_name=self.config.get('meet_name', 'Unknown Meet')
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

            # Bug 1: Use Entry_no if available
            entry_id_val = item.get('Entry_no')
            final_id = int(entry_id_val) if entry_id_val else idx

            result.append(meet_manager_pb2.Entry(
                id=final_id, 
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

    def _get_scoring_map(self):
        """Builds a lookup map for the Scoring table."""
        if hasattr(self, '_scoring_map') and self._scoring_map is not None:
            return self._scoring_map
        
        scoring_data = self._get_table('Scoring') or self._get_table('SCORING')
        self._scoring_map = {}
        for row in scoring_data:
            div = row.get('score_divno', '0')
            sex = row.get('score_sex', 'M').upper()
            place = self._safe_int(row.get('score_place', 0))
            
            if div not in self._scoring_map:
                self._scoring_map[div] = {}
            if sex not in self._scoring_map[div]:
                self._scoring_map[div][sex] = {}
            
            self._scoring_map[div][sex][place] = {
                'ind': self._safe_float(row.get('ind_score', 0)),
                'rel': self._safe_float(row.get('rel_score', 0))
            }
        return self._scoring_map

    def _calculate_points(self, item, sex, is_relay):
        """Calculates points for an entry or relay, with fallback to Scoring table."""
        # 1. Try pre-computed Ev_score
        score = self._safe_float(item.get('Ev_score', 0))
        if score > 0:
            return score
            
        # 2. Fallback to Scoring table
        place = self._safe_int(item.get('Fin_place', item.get('Place', 0)))
        if place <= 0:
            return 0.0
            
        div = item.get('Div_no', '0') or '0'
        # Map gender to Scoring table sexes (M/F)
        sex_map = {'B': 'M', 'M': 'M', 'G': 'F', 'W': 'F', 'F': 'F', 'X': 'M'} 
        mapped_sex = sex_map.get(sex.upper(), 'M')
        
        scoring_map = self._get_scoring_map()
        div_map = scoring_map.get(div, scoring_map.get('0', {}))
        sex_scores = div_map.get(mapped_sex, div_map.get('M', {}))
        
        score_data = sex_scores.get(place, {})
        return score_data.get('rel' if is_relay else 'ind', 0.0)

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
        event_raw_map = {} # Store raw event rows for sex lookup
        
        for e in self._get_table('Event'):
             e_no = e.get('Event_no') or e.get('Event_ptr')
             if not e_no: continue
             
             event_raw_map[e_no] = e
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
             
             # Lookup points
             ev_raw = event_raw_map.get(e_id, {})
             points = self._calculate_points(item, ev_raw.get('Event_sex', 'M'), False)
             
             # Only include scored items or finalists? 
             # Let's list everyone who has a place or time.
             if not item.get('Fin_Time') and place <= 0:
                  continue

             # Seed Time
             seed = item.get('ActualSeed_time') or item.get('ConvSeed_time') or item.get('Seed_Time') or 'NT'
             try:
                  if float(seed) == 0: seed = 'NT'
             except:
                  pass
             
             entry_obj = meet_manager_pb2.Entry(
                 id=0,
                 event_id=int(e_id),
                 athlete_id=int(ath_id if ath else 0),
                 athlete_name=f"{ath.get('First_name','')} {ath.get('Last_name','')}" if ath else "Unknown",
                 team_id=int(t_id),
                 team_name=teams_map.get(t_id, 'Unknown'),
                 seed_time=str(seed),
                 final_time=str(item.get('Fin_Time', '')),
                 place=place,
                 points=points,
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
             rel_ltr = item.get('Team_ltr', '')
             
             # Lookup points
             ev_raw = event_raw_map.get(e_id, {})
             points = self._calculate_points(item, ev_raw.get('Event_sex', 'X'), True)

             if not item.get('Fin_Time') and place <= 0:
                  continue

             # Seed Time
             seed = item.get('ActualSeed_time') or item.get('ConvSeed_time') or item.get('Seed_Time') or 'NT'
             try:
                  if float(seed) == 0: seed = 'NT'
             except:
                  pass

             entry_obj = meet_manager_pb2.Entry(
                 id=0,
                 event_id=int(e_id),
                 athlete_id=0,
                 athlete_name=f"Relay Team ({rel_ltr})" if rel_ltr else "Relay Team",
                 team_id=int(t_id if t_id else 0),
                 team_name=teams_map.get(t_id, 'Unknown'),
                 seed_time=str(seed),
                 final_time=str(item.get('Fin_Time', '')),
                 place=place,
                 points=points,
                 heat=self._safe_int(item.get('Fin_heat', 0)),
                 lane=self._safe_int(item.get('Fin_lane', 0)),
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

    def GenerateReport(self, request, context):
        print(f"Generating report: {request.type}, title: {request.title}")
        
        try:
            # 1. Convert our flat _data_cache into hierarchical hierarchical data using MmToJsonConverter
            converter = MmToJsonConverter(table_data=self._data_cache)
            hierarchical_data = converter.convert()
            
            # 2. Use ReportGenerator to create the PDF in a temporary file
            rg = ReportGenerator(hierarchical_data, title=request.title or "Meet Report")
            
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                temp_path = tmp.name
            
            report_type_map = {
                meet_manager_pb2.PSYCH: "psych",
                meet_manager_pb2.ENTRIES: "entries",
                meet_manager_pb2.LINEUPS: "lineups",
                meet_manager_pb2.RESULTS: "results"
            }
            
            rtype = report_type_map.get(request.type, "psych")
            
            if rtype == "psych":
                rg.generate_psych_sheet(temp_path)
            elif rtype == "entries":
                rg.generate_meet_entries(temp_path, team_filter=request.team_filter)
            elif rtype == "lineups":
                rg.generate_lineup_sheets(temp_path)
            elif rtype == "results":
                rg.generate_meet_results(temp_path)
            
            # 3. Read the generated PDF and return it as bytes
            with open(temp_path, 'rb') as f:
                pdf_content = f.read()
            
            # Clean up
            os.remove(temp_path)
            
            filename = f"report_{rtype}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            return meet_manager_pb2.ReportResponse(
                success=True,
                message="Report generated successfully",
                pdf_content=pdf_content,
                filename=filename
            )
            
        except Exception as e:
            print(f"Error generating report: {e}")
            import traceback
            traceback.print_exc()
            return meet_manager_pb2.ReportResponse(
                success=False,
                message=str(e)
            )

    def GetSessions(self, request, context):
        data = self._get_table('Session')
        # Need Meet Start Date to calculate session dates
        meets = self._get_table('Meet')
        meet_start = None
        if meets:
             # Try various keys for Start Date
             m = meets[0]
             date_str = m.get('Start') or m.get('Start_date') or ''
             if date_str:
                 try:
                     # Parse 07/15/2025 or similar
                     if " " in date_str: date_str = date_str.split(" ")[0]
                     for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d-%b-%y"):
                         try:
                             meet_start = datetime.datetime.strptime(date_str, fmt)
                             break
                         except ValueError:
                             continue
                 except:
                     pass

        sessions_to_process = []
        if data:
            for item in data:
                sessions_to_process.append({
                    'id': item.get('Sess_no'),
                    'name': item.get('Sess_name', f"Session {item.get('Sess_no')}"),
                    'day': item.get('Sess_day', 1),
                    'warmup': item.get('Sess_warmup', 0),
                    'starttime': item.get('Sess_starttime', 0),
                    'event_cnt': item.get('Event_cnt'),
                    'source_item': item
                })
        else:
            # Infer from Events
            event_table = self._get_table('Event') or self._get_table('MTEVENT')
            sess_ids = sorted(list(set(self._safe_int(e.get('Sess_no', e.get('sess_no', 1))) for e in event_table)))
            if not sess_ids and not event_table:
                 # Case: absolute zero data
                 sess_ids = [1]
            
            for s_id in sess_ids:
                sessions_to_process.append({
                    'id': str(s_id),
                    'name': "Session 1" if s_id == 1 and not event_table else f"Session {s_id}",
                    'day': 1,
                    'warmup': 0,
                    'starttime': 0,
                    'event_cnt': None,
                    'source_item': {}
                })
            
            # Override name for absolute zero case
            if not event_table and sessions_to_process:
                 sessions_to_process[0]['name'] = "All Events"

        sessions = []
        for i, s_info in enumerate(sessions_to_process):
            item = s_info['source_item']
            # Calculate date from Sess_day
            sess_date = ""
            day_offset = self._safe_int(s_info['day'], 1) - 1
            if meet_start and day_offset >= 0:
                 s_date = meet_start + datetime.timedelta(days=day_offset)
                 sess_date = s_date.strftime("%Y-%m-%d")
            else:
                 # Fallback to Sess_date if exists
                 sess_date = self._format_date(item.get('Sess_date', ''))

            # Calculate event count
            s_no = s_info['id']
            events = self._get_table('Event') or self._get_table('MTEVENT')
            ev_count = 0
            if s_no:
                 ev_count = sum(1 for e in events if str(e.get('Sess_no', e.get('sess_no', 1))) == str(s_no))

            sessions.append(meet_manager_pb2.Session(
                id=str(s_no),
                meet_id="1", 
                name=s_info['name'],
                date=sess_date,
                warm_up_time=self._seconds_to_time(s_info['warmup']),
                start_time=self._seconds_to_time(s_info['starttime']),
                event_count=s_info.get('event_cnt') or ev_count,
                session_num=self._safe_int(s_no, 0),
                day=self._safe_int(s_info['day'], 1)
            ))
        return meet_manager_pb2.SessionList(sessions=sessions)

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
