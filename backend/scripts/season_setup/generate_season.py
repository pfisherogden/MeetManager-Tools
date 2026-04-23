import os
import sys
import json
import logging
import argparse
import tempfile
import copy
from datetime import datetime, timedelta
import pandas as pd

# Robustly add the backend/src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "src"))
if backend_src_dir not in sys.path:
    sys.path.append(backend_src_dir)
sys.path.append(script_dir)

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.mdb_restorer import restore_db
from season_transformer import SeasonTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEDULE_2026 = [
    {"date": "2026-05-30", "name": "FAST vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False, "opponent": "FAST"},
    {"date": "2026-06-06", "name": "Del Prado vs Briarhill", "host": "Briarhill Cabana Club", "is_champs": False, "opponent": "BH"},
    {"date": "2026-06-13", "name": "Del Prado vs Meadows", "host": "Pleasanton Meadows", "is_champs": False, "opponent": "SHRK"},
    {"date": "2026-06-20", "name": "Castlewood vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False, "opponent": "CW"},
    {"date": "2026-06-27", "name": "Bay Club vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False, "opponent": "BCTW"},
    {"date": "2026-07-01", "name": "TVSL Extra Chance Meet", "host": "Foothill High School", "is_champs": False},
    {"date": "2026-07-11", "name": "Briarhill vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False, "opponent": "BH"},
    {"date": "2026-07-18", "name": "TVSL Championships", "host": "Foothill High School", "is_champs": True},
]

def load_config():
    config_path = os.path.join(script_dir, "config", "venues.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {"venues": {}, "teams": {}}

def get_lanes(host, config):
    return config.get("venues", {}).get(host, 6) # Default to 6

def get_team_name(abbr, config):
    return config.get("teams", {}).get(abbr, abbr)

def to_python(obj):
    """Recursively convert Java/Pandas objects to standard Python types."""
    if "java.lang.String" in str(type(obj)):
        return str(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {to_python(k): to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_python(x) for x in obj]
    return obj

def generate(template_path, output_dir, owner_team="DP"):
    # Base folder structure mirroring previous years
    season_data_dir = os.path.join(output_dir, "2026 Del Prado Data", "Swim Meets")
    if not os.path.exists(season_data_dir):
        os.makedirs(season_data_dir)

    print(f"Loading template: {template_path}")
    template_conv = MmToJsonConverter(mdb_path=template_path)
    
    # Export full schema including definitions
    full_template = template_conv.export_full_schema()
    # Normalize keys to Python strings in full_template too
    full_template["tables"] = {str(k): v for k, v in full_template["tables"].items()}
    
    config = load_config()

    first_meet_date = "2026-05-30"

    for meet in SCHEDULE_2026:
        # Create subfolder for each meet
        meet_dir_name = f"{meet['date']} {meet['name']}"
        meet_output_dir = os.path.join(season_data_dir, meet_dir_name)
        if not os.path.exists(meet_output_dir):
            os.makedirs(meet_output_dir)

        # Create standard subdirectories mirroring previous years
        for sub in ["reports", "backups", "results"]:
            os.makedirs(os.path.join(meet_output_dir, sub), exist_ok=True)

        print(f"\nGenerating MDB for: {meet['name']} ({meet['date']})")
        
        # We transform the ROWS inside the full_template
        current_rows = {tname: t_def["rows"] for tname, t_def in full_template["tables"].items()}
        current_rows = copy.deepcopy(current_rows)
        
        transformer = SeasonTransformer(current_rows)
        
        # 1. Purge data
        transformer.purge_data(preserve_team_abbr=owner_team)
        
        # 2. Update metadata
        lanes = get_lanes(meet["host"], config)
        
        # Date Logic
        if meet["date"] == first_meet_date:
            entry_open = "2025-06-01"
        else:
            entry_open = first_meet_date
            
        meet_dt = datetime.strptime(meet["date"], "%Y-%m-%d")
        deadline_dt = meet_dt - timedelta(days=4)
        entry_deadline = deadline_dt.strftime("%Y-%m-%d")

        transformer.update_meet(
            name=meet["name"],
            start_date=meet["date"],
            lanes=lanes,
            location=meet["host"],
            age_up="2026-06-01",
            entry_open=entry_open,
            entry_deadline=entry_deadline
        )
        
        # 3. Sessions
        transformer.consolidate_sessions(is_champs=meet["is_champs"])
        
        # 4. Scoring and Seeding
        transformer.setup_scoring_and_seeding()
        
        # 5. Ensure opponent team exists
        if "opponent" in meet:
            opp_name = get_team_name(meet["opponent"], config)
            transformer.ensure_team_exists(meet["opponent"], opp_name)

        # Build output_data with transformed rows
        output_data = {"tables": {}}
        
        # Start with all tables from the transformer (includes newly created ones)
        for tname, rows in transformer.table_data.items():
            if tname in full_template["tables"]:
                # Use existing schema
                t_def = copy.deepcopy(full_template["tables"][tname])
                t_def["rows"] = rows
                output_data["tables"][tname] = t_def
            else:
                # Create basic schema for new tables
                cols = []
                if rows:
                    for k in rows[0].keys():
                        cols.append({"name": k, "type": "TEXT"})
                output_data["tables"][tname] = {
                    "columns": cols,
                    "indexes": [],
                    "rows": rows
                }

        # Convert entire structure to Python types for JSON
        output_data = to_python(output_data)

        # Write to temp JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
            json.dump(output_data, tf)
            temp_json = tf.name

        # Restore to MDB
        filename = f"{meet['date']} {meet['name']}.mdb"
        target_mdb = os.path.join(meet_output_dir, filename)
        
        print(f"Restoring to {target_mdb}...")
        restore_db(temp_json, target_mdb)
        
        # Cleanup
        os.remove(temp_json)

    print(f"\nDone! All meets generated in {season_data_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, help="Path to blank template MDB")
    parser.add_argument("--output-dir", required=True, help="Directory to save generated MDBs")
    parser.add_argument("--owner-team", default="DP", help="The abbreviation of the host team to preserve in the MDB (default: DP)")
    args = parser.parse_args()

    generate(args.template, args.output_dir, args.owner_team)
