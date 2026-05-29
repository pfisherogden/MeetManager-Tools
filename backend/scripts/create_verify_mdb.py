import os
import sys
import copy
import json
from datetime import datetime

# Add paths
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "../src"))
sys.path.append(os.path.join(base_dir, "season_setup"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.mdb_restorer import restore_db
from season_transformer import SeasonTransformer
from populate_test_data import populate

def to_python(data):
    """Converts Java types and datetime to Python types for JSON serialization."""
    if isinstance(data, dict):
        return {str(k): to_python(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [to_python(v) for v in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data

def create_verify_mdb(template_path, output_mdb):
    print(f"Loading template: {template_path}")
    conv = MmToJsonConverter(template_path)
    full_template = conv.export_full_schema()
    full_template["tables"] = {str(k): v for k, v in full_template["tables"].items()}

    # Use first meet from schedule
    meet_def = {
        "name": "Verification Meet",
        "date": "2026-05-30",
        "host": "DP",
        "home": "DP",
        "away": "FAST",
        "is_champs": False
    }

    current_rows = {tname: t_def["rows"] for tname, t_def in full_template["tables"].items()}
    current_rows = copy.deepcopy(current_rows)
    transformer = SeasonTransformer(current_rows, table_defs=full_template["tables"])

    print("Transforming...")
    transformer.purge_data(preserve_team_abbr="DP")
    transformer.ensure_team_exists("DP", "Del Prado Stingrays")
    transformer.ensure_team_exists("FAST", "FAST Dolphins")
    
    transformer.update_meet(
        name=meet_def["name"],
        start_date=meet_def["date"],
        lanes=6,
        location="DP",
        is_champs=False,
        home_team="DP",
        away_team="FAST"
    )
    
    transformer.consolidate_sessions(is_champs=False)
    transformer.setup_scoring_and_seeding(is_champs=False)
    transformer.ensure_std_lanes()
    
    # 6. Memorized Reports
    transformer.inject_memorized_reports(team_abbr="DP")

    # Save to temp JSON
    temp_json = "temp_verify.json"
    output_data = {"tables": {}}
    for tname, rows in transformer.table_data.items():
        if tname in full_template["tables"]:
            t_def = copy.deepcopy(full_template["tables"][tname])
            t_def["rows"] = rows
            output_data["tables"][tname] = t_def
        else:
            # For new tables like MemorizedReports
            cols = [{"name": k, "type": "TEXT"} for k in rows[0].keys()] if rows else []
            output_data["tables"][tname] = {"columns": cols, "indexes": [], "rows": rows}
    
    # Convert entire structure to Python types for JSON
    output_data = to_python(output_data)
    
    with open(temp_json, 'w') as f:
        json.dump(output_data, f)

    print(f"Restoring to {output_mdb}...")
    restore_db(temp_json, output_mdb)
    
    # 7. Populate with synthetic data
    populate(output_mdb)
    
    # Cleanup
    if os.path.exists(temp_json):
        os.remove(temp_json)
    print("Verification MDB created successfully.")

if __name__ == "__main__":
    template = "/Users/pfo/Developer/season-setup/template.mdb"
    output = "/Users/pfo/Developer/tmp/verify_reports_final.mdb"
    if os.path.exists(output):
        os.remove(output)
    create_verify_mdb(template, output)
