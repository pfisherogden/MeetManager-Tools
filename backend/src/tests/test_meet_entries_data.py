
import logging
import os

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


import csv
import io
import subprocess


def load_mdb(db_path):
    print(f"Exporting tables from {db_path} using mdb-export...")
    try:
        tables = subprocess.check_output(["mdb-tables", "-1", db_path]).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error listing tables: {e}")
        return {}

    data = {}
    for t in tables:
        if not t.strip(): continue
        try:
             # -Q prevents quoting issues sometimes, but standard CSV is better
            csv_out = subprocess.check_output(["mdb-export", db_path, t]).decode("utf-8")
            # Parse CSV to list of dicts
            data[t] = list(csv.DictReader(io.StringIO(csv_out)))
        except Exception as e:
            print(f"Skipping table {t}: {e}")
    return data

def test_meet_entries_data():
    mdb_file = "/app/data/2025-07-12 FAST @ DP-Meet2-MeetMgr.mdb"
    if not os.path.exists(mdb_file):
        print(f"Error: MDB file not found at {mdb_file}")
        return

    print("Loading MDB...")
    table_data = load_mdb(mdb_file)
    converter = MmToJsonConverter(table_data=table_data)

    print("Extracting Report Data...")
    extractor = ReportDataExtractor(converter)

    # Extract data for all teams to find the problematic ones
    report_data = extractor.extract_meet_entries_data(team_filter=None)

    groups = report_data.get("groups", [])
    print(f"Extracted {len(groups)} team groups.")

    # 1. Check Age Group Strings
    print("\n--- Checking Age Group Strings ---")
    age_group_errors = 0
    for group in groups:
        for item in group.get("items", []):
            if "sub_items" in item: # Individual or Relay Team
                # Check headers for "0&U" or "7-0"
                header = item.get("header", "")

                # Verify Event Descriptions in sub_items
                for sub in item.get("sub_items", []):
                    desc = sub.get("desc", "")
                    # Look for suspicious patterns
                    if "0&U" in desc or "0-0" in desc or "9-0" in desc or "7-0" in desc:
                         print(f"WARN: Suspicious Age Group in Event: '{desc}' (Team: {group['header']}, Header: {header})")
                         age_group_errors += 1

                    # Also check for "0" as single age if likely error?
                    import re
                    if re.search(r'\b0\b', desc) and "Open" not in desc and "10" not in desc:
                         # e.g. "Girls 0 25 Free"
                         pass

    if age_group_errors == 0:
        print("No obvious Age Group errors found in descriptions (searching for 0&U, 9-0, etc).")
    else:
        print(f"Found {age_group_errors} potential Age Group errors.")

    # 2. Check Relay Duplication
    print("\n--- Checking Relay Swimmer Duplication ---")
    # We are looking for swimmers who appear twice: once as "Last, First" and once as part of "Name, Name..."
    # In the new logic, we split relay names.
    # Error: "Osborne, Maximilian", "Mitooka, Cole"... appearing as individuals when they only have relay entries?
    # Or appearing twice in the list?

    dupe_errors = 0
    for group in groups:
        team_name = group['header']
        seen_names = set()

        in_relay_section = False

        # Iterate formatted items
        for item in group.get("items", []):
            header = item.get("header", "")
            if "RELAY TEAMS" in header:
                in_relay_section = True
                continue

            if in_relay_section:
                continue

            # Extract name from header: "1  Last, First - ..."
            # Heuristic split
            try:
                # "1  Morrow, Katelyn - Female - Age: 11 - FAST - Ind/Rel: 0 / 2"
                parts = header.split(" - ")
                if not parts: continue
                name_part = parts[0] # "1  Morrow, Katelyn"
                # Strip sequence number
                name = " ".join(name_part.split(" ")[2:]) # remove "1  "
                # Actually sequence might be single digit.
                # Regex for "Seq  Name"
                import re
                m = re.match(r"^\d+\s+(.+)$", name_part)
                if m:
                    name = m.group(1).strip()

                if name in seen_names:
                    print(f"ERROR: Duplicate Swimmer in Report: '{name}' in {team_name}")
                    dupe_errors += 1
                seen_names.add(name)

            except Exception:
                # print(f"Error parsing header '{header}': {e}")
                pass

    if dupe_errors == 0:
        print("No Duplicate Swimmers found in report list.")

    # 3. Check Relay Teams Section correctness
    print("\n--- Checking Relay Teams Section ---")
    relay_sections = 0
    for group in groups:
        title_found = False
        for item in group.get("items", []):
            if "RELAY TEAMS" in item.get("header", ""):
                 title_found = True
                 relay_sections += 1
                 # Check sub_items are empty?
                 pass

            if title_found and "RELAY TEAMS" not in item.get("header", ""):
                # These should be relay entries
                # Check format "Semicolon separated names"
                sub = item.get("sub_items", [])
                if not sub: continue
                # We expect 2 rows: Time/HL and Names
                if len(sub) == 2:
                    # Row 1: Seq in idx, Team/Info in desc, Time in time, H/L in heat_lane
                    sub[0].get("idx", "")
                    info = sub[0].get("desc", "")
                    sub[0].get("time", "")
                    hl = sub[0].get("heat_lane", "")

                    # Row 2: Names in desc
                    names = sub[1].get("desc", "")

                    # 3a. Check H/L format (e.g. "1/7")
                    if "/" not in hl and hl != "":
                        print(f"WARN: Relay H/L not formatted as 'H/L': '{hl}'")

                    # 3b. Check Names format (Semicolon separated)
                    if ";" not in names and "," not in names:
                         print(f"WARN: Relay Entry names not formatted with names: '{names}'")

                    # 3c. Check Relay Letter in Info (Team - 'A')
                    if "Relay" not in info and "- '" not in info:
                        # Expect "Team - 'A'"
                        print(f"WARN: Relay Letter missing in info: '{info}'")

    print(f"Found {relay_sections} 'RELAY TEAMS' sections.")

    # 4. Check Relay Attribution to Individuals
    print("\n--- Checking Relay Attribution to Individuals ---")
    swimmers_with_relays = 0
    total_relay_events_in_ind = 0

    for group in groups:
        # iterate items
        for item in group.get("items", []):
            if "RELAY TEAMS" in item.get("header", ""): continue

            # Check Ind/Rel counts in header
            # "1  Last, First - ... - Ind/Rel: X / Y"
            header = item.get("header", "")
            try:
                parts = header.split("Ind/Rel:")
                if len(parts) > 1:
                    counts = parts[1].strip().split("/")
                    int(counts[0].strip())
                    rel_c = int(counts[1].strip())

                    # Verify event list matches
                    sub_items = item.get("sub_items", [])
                    relay_evts = [s for s in sub_items if "(Relay)" in s.get("desc", "")]

                    if rel_c > 0:
                        swimmers_with_relays += 1
                        total_relay_events_in_ind += len(relay_evts)

                        if len(relay_evts) != rel_c:
                            print(f"ERROR: Relay Count Mismatch for '{header}'. Expected {rel_c}, Found {len(relay_evts)}")

                    elif len(relay_evts) > 0:
                         print(f"ERROR: Found Relay Events but Count is 0 for '{header}'")

            except Exception:
                # print(f"Error checking counts: {e}")
                pass

    print(f"Found {swimmers_with_relays} swimmers with relay participation.")
    print(f"Total Relay Events listed under individuals: {total_relay_events_in_ind}")

    if swimmers_with_relays == 0:
        print("CRITICAL FAILURE: No relay events attributed to any individual swimmer!")

    # 5. Check Raw Age Data for specific teams
    print("\n--- Inspecting Raw Event Age Data ---")
    if "Event" in table_data:
        events = table_data["Event"]
        if events:
             # print(f"Event Table Columns: {list(events[0].keys())}")
             # import sys
             # sys.exit(0)
             pass

        for row in events:
            # Check for suspicious ages
            try:
                low = int(row.get("Low_age", 0))
                high = int(row.get("High_age", 0))
                evt_no = row.get("Event_no")
                dist = row.get("Event_dist")
                stroke = row.get("Event_stroke")

                # Check for "0-0" or "7-0" scenarios
                suspicious = False
                msg = ""
                if low == 0 and high == 0:
                     msg = "Low=0, High=0 (0&U?)"
                     suspicious = True
                elif low > 0 and high == 0:
                     msg = f"Low={low}, High=0 ({low}-0?)"
                     suspicious = True

                if suspicious:
                    print(f"EVENT #{evt_no} {dist}m {stroke}: {msg}")
            except: pass

    # 5. Check Relay Athlete IDs Availability
    print("\n--- Inspecting Relay Athlete Data Availability ---")
    if "RelayNames" in table_data:
        rn = table_data["RelayNames"]
        print(f"RelayNames table has {len(rn)} rows. Sample row keys: {list(rn[0].keys()) if rn else 'None'}")
    else:
        print("RelayNames table NOT found in extract.")

if __name__ == "__main__":
    test_meet_entries_data()

