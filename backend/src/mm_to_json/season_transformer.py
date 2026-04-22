import logging
import os
import json
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SeasonTransformer:
    def __init__(self, table_data: Dict[str, List[Dict[str, Any]]]):
        """
        Initializes the SeasonTransformer with table data.
        table_data is a dictionary where keys are table names and values are lists of dictionaries (records).
        """
        self.table_data = table_data
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
        }

    def _get_table_key(self, logical_name: str) -> Optional[str]:
        """Finds the actual key in table_data for a logical table name."""
        candidates = self.table_aliases.get(logical_name, [logical_name])
        for candidate in candidates:
            if candidate in self.table_data:
                return candidate
        return None

    def _get_table(self, logical_name: str) -> List[Dict[str, Any]]:
        """Returns the list of records for a logical table name, or an empty list if not found."""
        key = self._get_table_key(logical_name)
        if key:
            return self.table_data[key]
        return []

    def _set_table(self, logical_name: str, records: List[Dict[str, Any]]):
        """Updates the records for a logical table name."""
        key = self._get_table_key(logical_name)
        if key:
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
        
        # Clear transaction tables
        self._set_table("athlete", [])
        self._set_table("entry", [])
        self._set_table("relay", [])
        self._set_table("relaynames", [])

        # Load standard teams from venues.json if it exists
        standard_teams = {preserve_team_abbr}
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
            venues_path = os.path.join(config_dir, "venues.json")
            if os.path.exists(venues_path):
                with open(venues_path, "r") as f:
                    config = json.load(f)
                    standard_teams.update(config.get("teams", {}).keys())
        except Exception as e:
            logger.warning(f"Could not load venues.json for team filtering: {e}")

        # Filter TEAM table
        team_key = self._get_table_key("team")
        if team_key:
            teams = self.table_data[team_key]
            # Handle both TCode (Schema B) and other possible column names if necessary
            filtered_teams = [
                t for t in teams 
                if t.get("TCode") in standard_teams or t.get("tcode") in standard_teams
            ]
            self._set_table("team", filtered_teams)

    def update_meet(self, name: str, start_date: str, lanes: int, location: str = "", age_up: str = "2026-06-01"):
        """Updates the MEET table metadata."""
        meet_table = self._get_table("meet")
        if not meet_table:
            # Create a default row if missing
            meet_table = [{}]
        
        row = meet_table[0]
        # Update common column names (Schema A and B variants)
        names = ["meet_name1", "MEET_NAME1", "Meet_name1"]
        starts = ["meet_start", "MEET_START", "Meet_start"]
        ends = ["meet_end", "MEET_END", "Meet_end"]
        lanes_cols = ["meet_numlanes", "MEET_NUMLANES", "Meet_numlanes"]
        age_ups = ["calc_date", "CALC_DATE", "Calc_date"]
        locs = ["meet_location", "MEET_LOCATION", "Meet_location"]

        for col in names:
            row[col] = name
        for col in starts:
            row[col] = start_date
        for col in ends:
            row[col] = start_date
        for col in lanes_cols:
            row[col] = lanes
        for col in age_ups:
            row[col] = age_up
        if location:
            for col in locs:
                row[col] = location

        self._set_table("meet", meet_table)

    def consolidate_sessions(self, is_champs: bool = False):
        """
        Consolidates all events into a single session for non-champs meets.
        """
        if is_champs:
            logger.info("Champs meet detected, skipping session consolidation.")
            return

        logger.info("Consolidating sessions into 'Session 1'")
        
        # Set a single session
        new_sessions = [
            {
                "SESSION": 1,
                "SessName": "Session 1",
                "Day": 1,
                "StartTime": 480, # 8:00 AM in minutes
            }
        ]
        self._set_table("session", new_sessions)
        
        # Clear session items (mappings of events to sessions)
        self._set_table("sessitem", [])

        # Update all events to point to Session 1
        events = self._get_table("event")
        for event in events:
            # Update 'Session' column (common in Schema B / MTEVENT)
            if "Session" in event:
                event["Session"] = 1
            if "session" in event:
                event["session"] = 1
            if "SESSION" in event:
                event["SESSION"] = 1
        
        self._set_table("event", events)

    def ensure_team_exists(self, abbr: str, name: str):
        """Ensures a team exists in the TEAM table."""
        teams = self._get_table("team")
        exists = any(
            t.get("TCode") == abbr or t.get("tcode") == abbr 
            for t in teams
        )
        
        if not exists:
            logger.info(f"Adding missing team: {abbr} ({name})")
            new_team = {
                "TCode": abbr,
                "TName": name,
                "Short": name[:15], # Common length limit
                "LSC": "AB",
                "TType": "AGE"
            }
            teams.append(new_team)
            self._set_table("team", teams)
