import sys
import os
import json
import re
from typing import List, Dict, Any, Optional

# Add backend/src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, "../backend/src"))

from mm_to_json.mm_to_json import MmToJsonConverter  # noqa: E402


def get_age_group(age: int) -> str:
    """
    Categorizes a swimmer's age into a standard competition age group.

    Args:
        age: The age of the swimmer.

    Returns:
        The string representation of the age group (e.g., "7-8").
    """
    if age <= 6:
        return "6 & Under"
    if age <= 8:
        return "7-8"
    if age <= 10:
        return "9-10"
    if age <= 12:
        return "11-12"
    if age <= 14:
        return "13-14"
    return "15-18"


def extract_attendance_data(
    mdb_path: str, target_team_code: str = "DP"
) -> List[Dict[str, Any]]:
    """
    Extracts swimmer attendance and registration data from a Meet Manager MDB file.

    Args:
        mdb_path: The absolute path to the .mdb file.
        target_team_code: The team code to filter for (e.g., "DP").

    Returns:
        A list of dictionaries, each representing a swimmer and their event registrations.
    """
    converter = MmToJsonConverter(mdb_path)
    data = converter.convert()

    # Find team number for target team code
    team_no: Optional[int] = None
    team_df = converter.tables.get("team")
    if team_df is not None:
        mask = team_df["team_abbr"].str.strip() == target_team_code
        if mask.any():
            team_no = int(team_df[mask]["team_no"].iloc[0])

    if team_no is None:
        print(f"Team {target_team_code} not found in MDB")
        return []

    # Map athlete ID to their info and event flags
    athletes: Dict[int, Dict[str, Any]] = {}

    # Pre-populate from athlete table
    ath_df = converter.tables.get("athlete")
    if ath_df is not None:
        dp_athletes = ath_df[ath_df["team_no"] == team_no]
        for _, row in dp_athletes.iterrows():
            ath_id = int(row["ath_no"])
            pref_name = str(row.get("pref_name", "")).strip()
            first_name = str(row.get("first_name", "")).strip()

            athletes[ath_id] = {
                "ID": ath_id,
                "Last Name": str(row["last_name"]).strip(),
                "First Name": first_name,
                "Preferred Name": pref_name if pref_name else first_name,
                "Gender": str(row["ath_sex"]).strip(),
                "Age": int(row["ath_age"]),
                "Team": target_team_code,
                "Age Group": get_age_group(int(row["ath_age"])),
                "Free": "",
                "Back": "",
                "Breast": "",
                "Fly": "",
                "IM": "",
                "Free Relay": "",
                "Medley Relay": "",
            }

    # Extract events from the converted JSON
    for session in data.get("sessions", []):
        for event in session.get("events", []):
            is_relay = event.get("isRelay", False)
            event_desc = event.get("eventDesc", "").lower()

            # Classification logic
            stroke = "Unknown"
            if "freestyle relay" in event_desc or "free relay" in event_desc:
                stroke = "Free Relay"
            elif "medley relay" in event_desc:
                stroke = "Medley Relay"
            elif "freestyle" in event_desc or " free" in event_desc:
                stroke = "Free"
            elif "backstroke" in event_desc or " back" in event_desc:
                stroke = "Back"
            elif "breaststroke" in event_desc or " breast" in event_desc:
                stroke = "Breast"
            elif "butterfly" in event_desc or " fly" in event_desc:
                stroke = "Fly"
            elif "individual medley" in event_desc or re.search(r"\bim\b", event_desc):
                stroke = "IM"

            if stroke == "Unknown":
                continue

            for entry in event.get("entries", []):
                if entry.get("teamCode") == target_team_code:
                    # For relays, we need to iterate over relayAthletes
                    if is_relay and entry.get("relayAthletes"):
                        for ra in entry.get("relayAthletes"):
                            ath_id = ra.get("athleteId")
                            if ath_id in athletes:
                                athletes[ath_id][stroke] = "X"
                    else:
                        ath_id = entry.get("athleteId")
                        if ath_id in athletes:
                            athletes[ath_id][stroke] = "X"

    # Convert to list
    result = list(athletes.values())
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_attendance_data.py <path_to_mdb> [team_code]")
        sys.exit(1)

    mdb_path = sys.argv[1]
    team_code = sys.argv[2] if len(sys.argv) > 2 else "DP"

    swimmers = extract_attendance_data(mdb_path, target_team_code=team_code)

    output_path = "attendance_data.json"
    with open(output_path, "w") as f:
        json.dump(swimmers, f, indent=2)

    print(f"Extracted {len(swimmers)} swimmers to {output_path}")
