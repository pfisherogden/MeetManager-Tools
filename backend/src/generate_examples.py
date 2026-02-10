import os
import subprocess
import csv
import io
import datetime
import sys

# Add src to sys.path so we can import mm_to_json
sys.path.append(os.path.join(os.path.dirname(__file__)))

try:
    from mm_to_json.mm_to_json import MmToJsonConverter
    from mm_to_json.report_generator import ReportGenerator
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def load_mdb(path):
    cache = {}
    try:
        tables_out = subprocess.check_output(["mdb-tables", "-1", path]).decode('utf-8')
        tables = tables_out.strip().split()
        for table in tables:
            csv_out = subprocess.check_output(["mdb-export", path, table]).decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_out))
            cache[table] = list(reader)
        return cache
    except Exception as e:
        print(f"Error loading MDB: {e}")
        return {}

def main():
    # Use a real MDB from the data directory
    mdb_path = "data/2025-07-12 FAST @ DP-Meet2-MeetMgr.mdb"
    out_dir = "data/example_reports"
    os.makedirs(out_dir, exist_ok=True)
    
    if not os.path.exists(mdb_path):
        print(f"Error: {mdb_path} not found.")
        # Try to find any MDB
        data_dir = "data"
        for f in os.listdir(data_dir):
            if f.endswith(".mdb"):
                mdb_path = os.path.join(data_dir, f)
                break
        else:
            print("No MDB files found in data directory.")
            return

    print(f"Loading {mdb_path}...")
    table_data = load_mdb(mdb_path)
    
    # Initialize converter with table_data (skips mdb_writer/Jackcess)
    converter = MmToJsonConverter(table_data=table_data)
    hierarchical_data = converter.convert()
    
    reports = [
        ("psych", "Psych Sheet"),
        ("entries", "Meet Entries"),
        ("lineups", "Lineup Sheets"),
        ("results", "Meet Results")
    ]
    
    rg = ReportGenerator(hierarchical_data)
    
    for rtype, rname in reports:
        out_path = os.path.join(out_dir, f"example_{rtype}.pdf")
        rg.title = rname
        print(f"Generating {rname}...")
        try:
            if rtype == "psych":
                rg.generate_psych_sheet(out_path)
            elif rtype == "entries":
                rg.generate_meet_entries(out_path)
            elif rtype == "lineups":
                rg.generate_lineup_sheets(out_path)
            elif rtype == "results":
                rg.generate_meet_results(out_path)
            print(f"Saved to {out_path}")
        except Exception as e:
            print(f"Failed to generate {rtype}: {e}")

if __name__ == "__main__":
    main()
