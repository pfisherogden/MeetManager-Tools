import argparse
import logging
import os
import sys

# Robustly add the backend/src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "src"))
if backend_src_dir not in sys.path:
    sys.path.append(backend_src_dir)
sys.path.append(script_dir)

from season_transformer import SeasonTransformer  # noqa: E402

from mm_to_json.mm_to_json import MmToJsonConverter  # noqa: E402

logging.basicConfig(level=logging.INFO)

def validate(template_mdb, historical_mdbs, owner_team="DP"):
    # Load template data once
    print(f"Loading template: {template_mdb}")
    with MmToJsonConverter(mdb_path=template_mdb) as template_conv:
        full_template = template_conv.export_full_schema()
    full_template["tables"] = {str(k): v for k, v in full_template["tables"].items()}

    template_rows = {name: t_def["rows"] for name, t_def in full_template["tables"].items()}

    results = []

    for mdb_path in historical_mdbs:
        if not os.path.exists(mdb_path):
            print(f"Skipping missing file: {mdb_path}")
            continue

        print(f"\nValidating against: {mdb_path}")
        # Extract historical metadata
        with MmToJsonConverter(mdb_path=mdb_path) as target_conv:
            target_meet = target_conv.tables.get("meet").iloc[0]

        # Determine name, date, lanes, location
        name = target_meet.get("meet_name1")
        date = target_meet.get("meet_start")
        lanes = int(target_meet.get("meet_numlanes") or 6)
        location = target_meet.get("meet_location")

        if hasattr(date, 'timestamp'):
            age_up = f"{date.year}-06-01"
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = str(date)
            age_up = "2026-06-01" # Fallback

        print(f"Target: {name} | Date: {date_str} | Lanes: {lanes} | Location: {location}")

        # Transform template
        import copy
        current_data = copy.deepcopy(template_rows)
        transformer = SeasonTransformer(current_data, table_defs=full_template["tables"])

        transformer.purge_data(preserve_team_abbr=owner_team)
        transformer.update_meet(name, date_str, lanes, location=location, age_up=age_up)
        is_champs = "CHAMPS" in str(name).upper() or "CHAMPIONSHIP" in str(name).upper()
        transformer.consolidate_sessions(is_champs=is_champs)

        # Compare
        def get_table(data, logical):
            aliases = ["Meet", "MEET", "meet"] if logical == "meet" else ["Session", "SESSIONS", "session"]
            for a in aliases:
                if a in data: return data[a]  # noqa: E701
            return []

        transformed_meet = get_table(transformer.table_data, "meet")
        transformed_row = transformed_meet[0]

        mismatches = []
        # Case-insensitive check for name
        t_name = None
        for k, v in transformed_row.items():
            if k.lower() == "meet_name1":
                t_name = v
                break

        if t_name != name:
            mismatches.append(f"Name mismatch: {t_name} != {name}")

        # Case-insensitive check for lanes
        t_lanes = None
        for k, v in transformed_row.items():
            if k.lower() == "meet_numlanes":
                t_lanes = int(v)
                break

        if t_lanes != lanes:
            mismatches.append(f"Lanes mismatch: {t_lanes} != {lanes}")

        t_sessions = len(get_table(transformer.table_data, "session"))
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
