
import subprocess
import csv
import json
import os

MDB_PATH = "tmp/sample_data_champs_2025-aftermeet.mdb"
OUTPUT_DIR = "backend/tests/fixtures"

# List of all tables we probably need for full testing
TABLES = [
    "Relay", "RelayNames", "Entry", "Event", "Session", "Team", 
    "Scoring", "Athlete", "Meet", "St_s_no", "Sessitem", "Records", "RecordsApp", "Divisions"
]

def export_table(table):
    cmd = ["mdb-export", MDB_PATH, table]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8')
        reader = csv.DictReader(output.splitlines())
        rows = list(reader)
        return rows
    except Exception as e:
        print(f"Warning: Could not export {table}: {e}")
        return []

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    for table in TABLES:
        print(f"Exporting {table}...")
        data = export_table(table)
        if data:
            with open(f"{OUTPUT_DIR}/{table}.json", 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved {len(data)} rows to {OUTPUT_DIR}/{table}.json")
        else:
            print(f"Skipping empty/missing table {table}")

if __name__ == "__main__":
    main()
