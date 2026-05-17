import argparse
import copy
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta

# Robustly add the backend/src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "src"))
if backend_src_dir not in sys.path:
    sys.path.append(backend_src_dir)
sys.path.append(script_dir)

from season_transformer import SeasonTransformer  # noqa: E402

from mm_to_json.mdb_restorer import restore_db  # noqa: E402
from mm_to_json.mm_to_json import MmToJsonConverter  # noqa: E402
from mm_to_json.reporting.meet_event_writer import MeetEventWriter  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config():
    config_path = os.path.join(script_dir, "config", "venues.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {"venues": {}, "teams": {}}


def load_schedule(year):
    schedule_path = os.path.join(script_dir, "config", "schedule.json")
    if os.path.exists(schedule_path):
        with open(schedule_path) as f:
            full_schedule = json.load(f)
            return full_schedule.get(str(year))
    return None


def get_venue_info(host, config):
    info = config.get("venues", {}).get(host, {"lanes": 6, "address": ""})
    return info


def get_team_name(abbr, config):
    return config.get("teams", {}).get(abbr, abbr)


def to_python(obj):
    """Recursively convert Java/Pandas objects to standard Python types."""
    if "java.lang.String" in str(type(obj)):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {to_python(k): to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_python(x) for x in obj]
    return obj


def generate(template_path, output_dir, year, owner_team="DP"):
    schedule = load_schedule(year)
    if not schedule:
        logger.error(f"No schedule found for year {year} in config/schedule.json")
        return

    # Base folder structure mirroring previous years
    season_data_dir = os.path.join(output_dir, f"{year} Del Prado Data", "Swim Meets")
    if not os.path.exists(season_data_dir):
        os.makedirs(season_data_dir)

    print(f"Loading template: {template_path}")
    template_conv = MmToJsonConverter(mdb_path=template_path)

    # Export full schema including definitions
    full_template = template_conv.export_full_schema()
    # Normalize keys to Python strings in full_template too
    full_template["tables"] = {str(k): v for k, v in full_template["tables"].items()}

    config = load_config()

    # Find the first meet date for entry open logic
    meet_dates = sorted([m["date"] for m in schedule])
    first_meet_date = meet_dates[0] if meet_dates else ""

    for meet in schedule:
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

        transformer = SeasonTransformer(current_rows, table_defs=full_template["tables"])

        # 1. Purge data
        transformer.purge_data(preserve_team_abbr=owner_team)

        # 2. Ensure teams exist (must do before update_meet to get IDs)
        # Owner team
        owner_name = get_team_name(owner_team, config)
        transformer.ensure_team_exists(owner_team, owner_name)

        # Home/Away teams
        home_team = meet.get("home")
        away_team = meet.get("away")

        if home_team:
            h_name = get_team_name(home_team, config)
            transformer.ensure_team_exists(home_team, h_name)
        if away_team:
            a_name = get_team_name(away_team, config)
            transformer.ensure_team_exists(away_team, a_name)

        # 3. Update metadata
        # Default lanes from venue, or override from meet (e.g. Champs)
        v_info = get_venue_info(meet["host"], config)
        v_lanes = v_info.get("lanes", 6)
        lanes = meet.get("lanes", v_lanes)

        # Date Logic
        if meet["date"] == first_meet_date:
            # 6/1 of previous year
            try:
                dt = datetime.strptime(meet["date"], "%Y-%m-%d")
                entry_open = f"{dt.year - 1}-06-01"
            except Exception:
                entry_open = "2025-06-01"
        else:
            entry_open = first_meet_date

        meet_dt = datetime.strptime(meet["date"], "%Y-%m-%d")
        deadline_dt = meet_dt - timedelta(days=4)
        entry_deadline = deadline_dt.strftime("%Y-%m-%d")

        # Age up is usually 6/1 of current year
        age_up = f"{year}-06-01"

        transformer.update_meet(
            name=meet["name"],
            start_date=meet["date"],
            lanes=lanes,
            location=meet["host"],
            address=v_info.get("address", ""),
            city=v_info.get("city", ""),
            state=v_info.get("state", ""),
            zip_code=v_info.get("zip", ""),
            age_up=age_up,
            entry_open=entry_open,
            entry_deadline=entry_deadline,
            owner_team=owner_team,
            home_team=home_team,
            away_team=away_team,
            is_champs=meet["is_champs"],
        )

        # 4. Sessions
        transformer.consolidate_sessions(is_champs=meet["is_champs"])

        # 5. Scoring and Seeding
        transformer.setup_scoring_and_seeding(is_champs=meet["is_champs"])
        transformer.ensure_std_lanes()

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
                output_data["tables"][tname] = {"columns": cols, "indexes": [], "rows": rows}

        # Convert entire structure to Python types for JSON
        output_data = to_python(output_data)

        # Write to temp JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump(output_data, tf)
            temp_json = tf.name

        # Restore to MDB
        filename = f"{meet['date']} {meet['name']}-audit-v4.mdb"
        target_mdb = os.path.join(meet_output_dir, filename)

        print(f"Restoring to {target_mdb}...")
        restore_db(temp_json, target_mdb)

        # 6. Export to Team Manager (ZIP with EV3/HYV)
        # Find required tables logically
        meet_keys = transformer._get_all_table_keys("meet")
        event_keys = transformer._get_all_table_keys("event")
        session_keys = transformer._get_all_table_keys("session")
        scoring_keys = transformer._get_all_table_keys("scoring")

        if meet_keys and event_keys:
            meet_info = transformer.table_data[meet_keys[0]][0]
            events = transformer.table_data[event_keys[0]]
            sessions = transformer.table_data[session_keys[0]] if session_keys else []
            scoring = transformer.table_data[scoring_keys[0]] if scoring_keys else []

            # Format filename as MM/DD/YYYY -> MMDDYYYY
            m_date = datetime.strptime(meet["date"], "%Y-%m-%d").strftime("%d%b%Y")
            zip_filename = f"Meet Events-{meet['name']}-{m_date}-001.zip"
            target_zip = os.path.join(meet_output_dir, zip_filename)

            writer = MeetEventWriter(meet_info, sessions, events, scoring)
            writer.write_to_zip(target_zip)
            print(f"Exported Team Manager events to {target_zip}")

        # Cleanup
        os.remove(temp_json)

    print(f"\nDone! All meets generated in {season_data_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, help="Path to blank template MDB")
    parser.add_argument("--output-dir", required=True, help="Directory to save generated MDBs")
    parser.add_argument("--year", type=int, default=2026, help="The season year (default: 2026)")
    parser.add_argument(
        "--owner-team",
        default="DP",
        help="The abbreviation of the host team to preserve in the MDB (default: DP)",
    )
    args = parser.parse_args()

    generate(args.template, args.output_dir, args.year, args.owner_team)
