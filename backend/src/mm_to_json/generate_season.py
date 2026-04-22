import os
import sys
import json
import logging
import argparse
import tempfile
import copy
from datetime import datetime

# Add the backend/src to path for imports
sys.path.append(os.path.join(os.getcwd(), "MeetManager-Tools", "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.season_transformer import SeasonTransformer
from mm_to_json.mdb_restorer import restore_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEDULE_2026 = [
    {"date": "2026-05-30", "name": "FAST vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False},
    {"date": "2026-06-06", "name": "Del Prado vs Briarhill", "host": "Briarhill Cabana Club", "is_champs": False},
    {"date": "2026-06-13", "name": "Del Prado vs Meadows", "host": "Pleasanton Meadows", "is_champs": False},
    {"date": "2026-06-20", "name": "Castlewood vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False},
    {"date": "2026-06-27", "name": "Bay Club vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False},
    {"date": "2026-07-01", "name": "TVSL Extra Chance Meet", "host": "Foothill High School", "is_champs": False},
    {"date": "2026-07-11", "name": "Briarhill vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False},
    {"date": "2026-07-18", "name": "TVSL Championships", "host": "Foothill High School", "is_champs": True},
]

def get_lanes(host):
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "venues.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            return config.get("venues", {}).get(host, 6) # Default to 6
    return 6

class PandasEncoder(json.JSONEncoder):
    def default(self, obj):
        # Handle Java strings from JPype
        if "java.lang.String" in str(type(obj)):
            return str(obj)
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        import pandas as pd
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%dT%H:%M:%S')
        if "Timestamp" in str(type(obj)):
            return obj.isoformat()
        return super().default(obj)

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

def generate(template_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Loading template: {template_path}")
    template_conv = MmToJsonConverter(mdb_path=template_path)
    
    # Export full schema including definitions
    full_template = template_conv.export_full_schema()

    for meet in SCHEDULE_2026:
        print(f"\nGenerating MDB for: {meet['name']} ({meet['date']})")
        
        # We need to transform the ROWS inside the full_template
        # Create a simplified table_data for the transformer
        current_rows = {tname: t_def["rows"] for tname, t_def in full_template["tables"].items()}
        
        # Deep copy the rows
        current_rows = copy.deepcopy(current_rows)
        transformer = SeasonTransformer(current_rows)
        
        # 1. Purge data
        transformer.purge_data()
        
        # 2. Update metadata
        lanes = get_lanes(meet["host"])
        transformer.update_meet(
            name=meet["name"],
            start_date=meet["date"],
            lanes=lanes,
            location=meet["host"],
            age_up="2026-06-01"
        )
        
        # 3. Sessions
        transformer.consolidate_sessions(is_champs=meet["is_champs"])
        
        # 4. Ensure Team CW
        transformer.ensure_team_exists("CW", "Castlewood")

        # Now put the transformed rows back into the full structure
        output_data = copy.deepcopy(full_template)
        for tname, rows in current_rows.items():
            if tname in output_data["tables"]:
                output_data["tables"][tname]["rows"] = rows

        # Convert entire structure to Python types for JSON
        output_data = to_python(output_data)

        # Write to temp JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
            json.dump(output_data, tf)
            temp_json = tf.name

        # Restore to MDB
        filename = f"{meet['date']}_{meet['name'].replace(' ', '_')}.mdb"
        target_mdb = os.path.join(output_dir, filename)
        
        print(f"Restoring to {target_mdb}...")
        restore_db(temp_json, target_mdb)
        
        # Cleanup
        os.remove(temp_json)

    print(f"\nDone! All meets generated in {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, help="Path to blank template MDB")
    parser.add_argument("--output-dir", required=True, help="Directory to save generated MDBs")
    args = parser.parse_args()

    generate(args.template, args.output_dir)
