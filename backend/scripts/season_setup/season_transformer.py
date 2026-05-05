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
            "stdlanes": ["Stdlanes", "STDLANES", "stdlanes"],
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

    def update_meet(self, name: str, start_date: str, lanes: int, location: str = "", address: str = "", age_up: str = "2026-06-01", entry_open: str = "", entry_deadline: str = "", owner_team: str = "DP", opponent_team: Optional[str] = None):
        """Updates the MEET table metadata across all possible aliases."""
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
                "eligibility": ["entryeligibility_date", "ENTRYELIGIBILITY_DATE"],
                "entrymax_total": ["entrymax_total", "ENTRYMAX_TOTAL"],
                "indmax_perath": ["indmax_perath", "INDMAX_PERATH"],
                "relmax_perath": ["relmax_perath", "RELMAX_PERATH"],
                "addr1": ["meet_addr1", "MEET_ADDR1"],
                "dual_evenodd": ["dual_evenodd", "DUAL_EVENODD"],
                "team_evenlanes": ["team_evenlanes", "TEAM_EVENLANES"],
                "team_oddlanes": ["team_oddlanes", "TEAM_ODDLANES"]
            }

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
                "indmaxscorers": 4,
                "eligibility": self._date_to_ms(entry_open),
                "entrymax_total": 4,
                "indmax_perath": 3,
                "relmax_perath": 2,
                "addr1": address,
                "dual_evenodd": True,
                "team_evenlanes": self.team_ids.get(owner_team.upper(), 0),
                "team_oddlanes": self.team_ids.get(opponent_team.upper(), 0) if opponent_team else 0
            }

            for record in meet_table:
                # Use a list of actual columns to be safe
                actual_cols = list(record.keys())
                # Ensure all mapped columns exist in the record if they are missing
                for prop, candidates in mappings.items():
                    found = False
                    for actual_col in actual_cols:
                        if str(actual_col).lower() in [c.lower() for c in candidates]:
                            found = True
                            if values[prop] is not None:
                                record[actual_col] = values[prop]
                            break
                    if not found and values[prop] is not None:
                        # Add the preferred candidate name
                        record[candidates[0]] = values[prop]

    def setup_scoring_and_seeding(self):
        """Applies standard scoring and seeding rules."""
        for key in self._get_all_table_keys("scoring"):
            scoring = self.table_data[key]
            if scoring:
                # Dual meet standard: 5-3-2-1 for individual, 10-6 for relays
                ind_points = {1: 5.0, 2: 3.0, 3: 2.0, 4: 1.0}
                rel_points = {1: 10.0, 2: 6.0}
                
                for row in scoring:
                    actual_cols = {k.lower(): k for k in row.keys()}
                    
                    if "score_place" in actual_cols:
                        place = row[actual_cols["score_place"]]
                        if "ind_score" in actual_cols:
                            row[actual_cols["ind_score"]] = ind_points.get(place, 0.0)
                        if "rel_score" in actual_cols:
                            row[actual_cols["rel_score"]] = rel_points.get(place, 0.0)
                    else:
                        # Fallback for ind1, ind2, ... structure
                        for i, val in enumerate([5, 3, 2, 1, 0], 1):
                            target = f"ind{i}"
                            if target in actual_cols:
                                row[actual_cols[target]] = val
                        for i, val in enumerate([10, 6, 0], 1):
                            target = f"rel{i}"
                            if target in actual_cols:
                                row[actual_cols[target]] = val

    def consolidate_sessions(self, is_champs: bool = False):
        """Consolidates all events into a single session for non-champs meets."""
        if is_champs:
            return

        logger.info("Consolidating sessions into 'Session 1'")
        sess_ptr = 1
        
        session_keys = self._get_all_table_keys("session")
        
        # Comprehensive session record
        new_session = {
            "Sess_no": 1,
            "Sess_ltr": " ",
            "Sess_ptr": sess_ptr,
            "Sess_day": 1,
            "Sess_starttime": 32400, # 9:00 AM (9 * 3600)
            "Sess_entrymax": 0,
            "Sess_name": "All",
            "Sess_interval": 60,
            "Sess_course": "Y",
            "Sess_entrymaxind": 0,
            "Sess_entrymaxrel": 0,
            "Sess_backinterval": 15,
            "Sess_divinginterval": 30,
            "Sess_chaseinterval": 0
        }

        if not session_keys:
            self._set_table("session", [new_session])
        else:
            for key in session_keys:
                self.table_data[key] = [new_session]
        
        for key in self._get_all_table_keys("sessitem"):
            self.table_data[key] = []

        new_sessitems = []
        event_keys = self._get_all_table_keys("event")
        if event_keys:
            events = self.table_data[event_keys[0]]
            for i, event in enumerate(events, 1):
                # Try multiple PTR candidates
                e_ptr = event.get("Event_ptr") or event.get("event_ptr") or event.get("Event") or i
                new_sessitems.append({
                    "Sess_order": i, "Sess_ptr": sess_ptr, "Event_ptr": e_ptr,
                    "Sess_rnd": "F", "Rept_type": " ", "Delay_seconds": 0, "Alt_With": False
                })
            self._set_table("sessitem", new_sessitems)

        for key in event_keys:
            for event in self.table_data[key]:
                for actual_col in event.keys():
                    if str(actual_col).lower() == "session":
                        event[actual_col] = 1

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
                    # Create empty record from columns
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
                    # Fallback for empty table and no defs
                    new_team = {
                        "TCode": abbr, "TName": name, "Short": name[:15],
                        "LSC": "CC", "TType": "AGE", "Team_no": new_id
                    }
                    teams.append(new_team)
                
                self.team_ids[abbr.upper()] = new_id
                self.table_data[key] = teams
