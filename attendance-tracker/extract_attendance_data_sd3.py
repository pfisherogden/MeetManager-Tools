import sys
import os
import json
from typing import List, Dict, Any, Optional

# Add paths
sys.path.append(os.path.join(os.getcwd(), "MeetManager-Tools/attendance-tracker"))


def get_age_group(age: int) -> str:
    """
    Categorizes a swimmer's age into a standard competition age group.
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


def extract_attendance_data_sd3(
    file_path: str, target_team: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Extracts swimmer attendance and registration data from a TeamUnify SD3 file.

    Args:
        file_path: The absolute path to the .sd3 file.
        target_team: Optional team code to filter for. If None, all in file are returned.

    Returns:
        A list of dictionaries, each representing a swimmer and their event registrations.
    """
    athletes: Dict[str, Dict[str, Any]] = {}

    with open(file_path, "rb") as f:
        # Fixed-width lines, decode as ascii to handle potential garbage
        lines = [line.decode("ascii", errors="ignore") for line in f]

    # First pass: find all athletes and their basic info from D0
    for line in lines:
        if line.startswith("D0"):
            # Team code in D0 is at pos 6 length 6 (index 5-11) according to some specs,
            # but in this file it seems to be blank or varied.
            # We'll default to 'DP' if blank, or use provided target_team.
            team = line[5:11].strip()
            if target_team and team and team != target_team:
                continue

            # USS ID: pos 40 len 12 -> Index 39:51
            ussn = line[39:51].strip()
            # Full Name: pos 12 len 28 -> Index 11:39
            full_name = line[11:39].strip()
            if "," in full_name:
                last, first = full_name.split(",", 1)
            else:
                last, first = full_name, ""

            last = last.strip()
            first = first.strip()
            ath_id = ussn if ussn else full_name

            if ath_id not in athletes:
                # Sex: pos 66 len 1 -> Index 65
                sex = line[65]
                # Age: pos 64 len 2 -> Index 63:65
                age_str = line[63:65].strip()
                age = int(age_str) if age_str.isdigit() else 0

                athletes[ath_id] = {
                    "ID": ath_id,
                    "Last Name": last,
                    "First Name": first,
                    "Preferred Name": first,
                    "Gender": sex,
                    "Age": age,
                    "Team": team if team else "DP",
                    "Age Group": get_age_group(age),
                    "Medley Relay": "",
                    "Free Relay": "",
                    "Free": "",
                    "Back": "",
                    "Breast": "",
                    "Fly": "",
                    "IM": "",
                }

            # Stroke Code: pos 72 len 1 -> Index 71
            stroke_code = line[71]
            stroke_map = {
                "1": "Free",
                "2": "Back",
                "3": "Breast",
                "4": "Fly",
                "5": "IM",
            }
            if stroke_code in stroke_map:
                athletes[ath_id][stroke_map[stroke_code]] = "X"

    # Second pass: preferred name from D3
    for line in lines:
        if line.startswith("D3"):
            # USS ID in D3: pos 3 len 14? We use the first 12 to match D0.
            ussn_long = line[2:16].strip()
            ussn_short = ussn_long[:12]
            # Preferred Name: pos 17 len 15 -> Index 16:31
            pref = line[16:31].strip()
            if ussn_short in athletes and pref:
                athletes[ussn_short]["Preferred Name"] = pref

    # Third pass: Relays from E0/F0
    current_relay_stroke = None
    for line in lines:
        if line.startswith("E0"):
            # Stroke: pos 26 len 1 -> Index 25
            stroke_code = line[25]
            if stroke_code == "6":
                current_relay_stroke = "Free Relay"
            elif stroke_code == "7":
                current_relay_stroke = "Medley Relay"
            else:
                current_relay_stroke = None
        elif line.startswith("F0") and current_relay_stroke:
            # USS ID in F0: pos 46 len 12 -> Index 45:57
            ussn = line[45:57].strip()
            if ussn in athletes:
                athletes[ussn][current_relay_stroke] = "X"
            else:
                # Try name match: pos 18 len 28 -> Index 17:45
                name = line[17:45].strip()
                # Remove relay letter prefix (A/B/C) if found
                if len(name) > 1 and name[0] in "ABCDEF":
                    name = name[1:].strip()
                for ath in athletes.values():
                    # Substring check for robustness
                    if f"{ath['Last Name']}, {ath['First Name']}" in name:
                        ath[current_relay_stroke] = "X"
                        break

    return list(athletes.values())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_attendance_data_sd3.py <path_to_sd3> [team_code]")
        sys.exit(1)

    file_path = sys.argv[1]
    target_team = sys.argv[2] if len(sys.argv) > 2 else None

    swimmers = extract_attendance_data_sd3(file_path, target_team=target_team)

    output_path = "attendance_data.json"
    with open(output_path, "w") as f:
        json.dump(swimmers, f, indent=2)

    print(f"Extracted {len(swimmers)} swimmers from SD3 to {output_path}")
