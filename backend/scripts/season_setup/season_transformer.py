import logging
import os
import json
import copy
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SeasonTransformer:
    def __init__(self, table_data: Dict[str, List[Dict[str, Any]]]):
        """
        Initializes the SeasonTransformer with table data.
        table_data is a dictionary where keys are table names and values are lists of dictionaries (records).
        Important: Ensures all keys are converted to Python strings.
        """
        # Convert all keys to standard Python strings to avoid java.lang.String issues
        self.table_data = {str(k): v for k, v in table_data.items()}
        
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
            logger.info(f"Creating new table in transformer dataset: {default_key}")
            self.table_data[default_key] = records

    def purge_data(self, preserve_team_abbr: str = "DP"):
        """
        Empties ATHLETE, ENTRY, RELAY, and RELAYNAMES tables.
        Filters TEAM table to keep only standard teams from venues.json or the preserved team.
        """
        logger.info(f"Purging data (preserving team: {preserve_team_abbr})")
        
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
            filtered_teams = [
                t for t in teams 
                if str(t.get("TCode") or t.get("tcode") or "").upper() in standard_teams
            ]
            self.table_data[key] = filtered_teams

    def update_meet(self, name: str, start_date: str, lanes: int, location: str = "", age_up: str = "2026-06-01", entry_open: str = "", entry_deadline: str = ""):
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
                "open": ["entry_open", "ENTRY_OPEN", "Entry_open"],
                "deadline": ["entry_deadline", "ENTRY_DEADLINE", "Entry_deadline"]
            }

            values = {
                "name": name, "start": start_date, "end": start_date, "lanes": lanes,
                "age_up": age_up, "location": location, "open": entry_open, "deadline": entry_deadline
            }

            for record in meet_table:
                for actual_col in list(record.keys()):
                    for prop, candidates in mappings.items():
                        if str(actual_col).lower() in [c.lower() for c in candidates]:
                            if values[prop] is not None:
                                record[actual_col] = values[prop]

    def setup_scoring_and_seeding(self):
        """Applies standard scoring and seeding rules."""
        for key in self._get_all_table_keys("scoring"):
            scoring = self.table_data[key]
            if scoring:
                for row in scoring:
                    for i, val in enumerate([5, 3, 2, 1], 1):
                        for actual_col in row.keys():
                            if str(actual_col).lower() == f"ind{i}":
                                row[actual_col] = val
                    for i, val in enumerate([10, 6], 1):
                        for actual_col in row.keys():
                            if str(actual_col).lower() == f"rel{i}":
                                row[actual_col] = val

    def consolidate_sessions(self, is_champs: bool = False):
        """
        Consolidates all events into a single session for non-champs meets.
        """
        if is_champs:
            return

        logger.info("Consolidating sessions into 'Session 1'")
        
        # 1. Create the single session
        sess_ptr = 1
        new_session = {
            "Sess_no": 1,
            "Sess_ltr": " ",
            "Sess_ptr": sess_ptr,
            "Sess_day": 1,
            "Sess_starttime": 480,
            "Sess_name": "Session 1",
        }
        
        # Update Session table across all aliases
        session_keys = self._get_all_table_keys("session")
        if not session_keys:
            self._set_table("session", [new_session])
        else:
            for key in session_keys:
                old_sessions = self.table_data[key]
                if not old_sessions:
                    self.table_data[key] = [new_session]
                else:
                    base = copy.deepcopy(old_sessions[0])
                    for col in base.keys():
                        if col.lower() == "sess_no": base[col] = 1
                        if col.lower() == "sess_ptr": base[col] = sess_ptr
                        if col.lower() == "sess_day": base[col] = 1
                        if col.lower() == "sess_starttime": base[col] = 480
                        if col.lower() == "sess_name": base[col] = "Session 1"
                    self.table_data[key] = [base]
        
        # 2. Map all events to this session in Sessitem
        new_sessitems = []
        events = []
        event_keys = self._get_all_table_keys("event")
        if event_keys:
            events = self.table_data[event_keys[0]]

        for i, event in enumerate(events, 1):
            e_ptr = event.get("Event_ptr") or event.get("event_ptr") or i
            new_sessitems.append({
                "Sess_order": i,
                "Sess_ptr": sess_ptr,
                "Event_ptr": e_ptr,
                "Sess_rnd": "F",
                "Rept_type": " ",
                "Delay_seconds": 0,
                "Alt_With": False,
            })
            
        self._set_table("sessitem", new_sessitems)

        # 3. Update legacy session column in Event if it exists
        for key in event_keys:
            for event in self.table_data[key]:
                for actual_col in list(event.keys()):
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
            exists = any(
                str(t.get("TCode") or t.get("tcode") or "").upper() == str(abbr).upper()
                for t in teams
            )
            
            if not exists:
                logger.info(f"Adding missing team: {abbr} ({name}) to {key}")
                new_team = {
                    "TCode": abbr,
                    "TName": name,
                    "Short": name[:15],
                    "LSC": "AB",
                    "TType": "AGE"
                }
                teams.append(new_team)
                self.table_data[key] = teams
