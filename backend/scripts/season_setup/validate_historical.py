import os
import sys
import json
import logging
import argparse
from datetime import datetime

# Robustly add the backend/src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "src"))
if backend_src_dir not in sys.path:
    sys.path.append(backend_src_dir)
sys.path.append(script_dir)

from mm_to_json.mm_to_json import MmToJsonConverter
from season_transformer import SeasonTransformer

logging.basicConfig(level=logging.INFO)

def validate(template_mdb, historical_mdbs, owner_team="DP"):
    # Load template data once
    print(f"Loading template: {template_mdb}")
    template_conv = MmToJsonConverter(mdb_path=template_mdb)
    template_data = {name: df.to_dict('records') for name, df in template_conv.tables.items()}

    results = []

    for mdb_path in historical_mdbs:
        if not os.path.exists(mdb_path):
            print(f"Skipping missing file: {mdb_path}")
            continue

        print(f"\nValidating against: {mdb_path}")
        # Extract historical metadata
        target_conv = MmToJsonConverter(mdb_path=mdb_path)
        target_meet = target_conv.tables.get("meet").iloc[0]
        
        # Determine name, date, lanes, location
        name = target_meet.get("Meet_name1") or target_meet.get("meet_name1")
        date = target_meet.get("Meet_start") or target_meet.get("meet_start")
        lanes = int(target_meet.get("Meet_numlanes") or target_meet.get("meet_numlanes") or 6)
        location = target_meet.get("Meet_location") or target_meet.get("meet_location")
        
        if isinstance(date, datetime):
            age_up = f"{date.year}-06-01"
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = str(date)
            age_up = "2026-06-01" # Fallback

        print(f"Target: {name} | Date: {date_str} | Lanes: {lanes} | Location: {location}")

        # Transform template
        import copy
        current_data = copy.deepcopy(template_data)
        transformer = SeasonTransformer(current_data)
        
        transformer.purge_data(preserve_team_abbr=owner_team)
        transformer.update_meet(name, date_str, lanes, location=location, age_up=age_up)
        is_champs = "CHAMPS" in name.upper() or "CHAMPIONSHIP" in name.upper()
        transformer.consolidate_sessions(is_champs=is_champs)
        
        # Compare
        transformed_meet = current_data.get("Meet") or current_data.get("MEET") or current_data.get("meet")
        transformed_row = transformed_meet[0]
        
        mismatches = []
        t_name = transformed_row.get("Meet_name1") or transformed_row.get("meet_name1")
        if t_name != name:
            mismatches.append(f"Name mismatch: {t_name} != {name}")
            
        t_lanes = transformed_row.get("Meet_numlanes") or transformed_row.get("meet_numlanes")
        if int(t_lanes) != lanes:
            mismatches.append(f"Lanes mismatch: {t_lanes} != {lanes}")
            
        t_sessions = len(current_data.get("Session") or current_data.get("SESSIONS") or current_data.get("session"))
        if not is_champs and t_sessions != 1:
            mismatches.append(f"Session count mismatch: {t_sessions} != 1 for dual meet")

        if not mismatches:
            print("✅ SUCCESS: Metadata matches.")
            results.append((mdb_path, True))
        else:
            print(f"❌ FAILURE: {', '.join(mismatches)}")
            results.append((mdb_path, False))

    print("\n" + "="*40)
    print("FINAL VALIDATION REPORT")
    print("="*40)
    for path, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status}: {path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, help="Path to blank template MDB")
    parser.add_argument("--historical-files", nargs='+', required=True, help="Paths to historical MDBs for comparison")
    parser.add_argument("--owner-team", default="DP", help="The abbreviation of the host team to preserve in the MDB (default: DP)")
    args = parser.parse_args()

    validate(args.template, args.historical_files, args.owner_team)
