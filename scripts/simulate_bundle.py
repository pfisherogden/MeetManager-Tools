import csv
import io
import os
import subprocess
import sys
import json

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "backend/src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def load_mdb(db_path):
    print(f"Exporting tables from {db_path} using mdb-export...")
    try:
        tables = subprocess.check_output(["mdb-tables", "-1", db_path]).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error listing tables: {e}")
        return {}

    data = {}
    for t in tables:
        if not t.strip():
            continue
        try:
            csv_out = subprocess.check_output(["mdb-export", db_path, t]).decode("utf-8")
            data[t] = list(csv.DictReader(io.StringIO(csv_out)))
        except Exception as e:
            print(f"Skipping table {t}: {e}")
    return data

def simulate_extraction():
    data_path = "backend/data/sample_data_champs_2025-aftermeet.mdb"
    if not os.path.exists(data_path):
        data_path = "../backend/data/sample_data_champs_2025-aftermeet.mdb"
        if not os.path.exists(data_path):
            print(f"Error: {data_path} not found.")
            return

    print(f"Loading MDB from {data_path}...")
    table_data = load_mdb(data_path)
    
    # Simulate fresh instance as in server.py
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    reports_to_gen = [
        ("program", "Meet Program"),
        ("results", "Meet Results"),
        ("entries", "Meet Entries"),
    ]

    for rtype, title in reports_to_gen:
        print(f"\n--- Simulating Extraction for {title} ---")
        
        if rtype == "program":
            report_data = extractor.extract_meet_program_data(report_title=title)
        elif rtype == "results":
            report_data = extractor.extract_results_data(report_title=title)
        else:
            report_data = extractor.extract_meet_entries_data(report_title=title)

        groups = report_data.get("groups", [])
        print(f"RESULT: {title} has {len(groups)} groups")
        
        if not groups:
            print(f"ERROR: {title} has NO groups!")
            continue

        total_items = 0
        empty_items_groups = 0
        
        for g in groups:
            items = g.get("items", [])
            total_items += len(items)
            if not items:
                empty_items_groups += 1
                # print(f"  WARNING: Group '{g.get('header')}' has NO items!")
        
        print(f"RESULT: Total items across all groups: {total_items}")
        if empty_items_groups > 0:
            print(f"WARNING: {empty_items_groups} groups had NO 'items' key data!")

if __name__ == "__main__":
    simulate_extraction()
