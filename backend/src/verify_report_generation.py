import csv
import io
import os
import subprocess
import sys
import json

# Ensure mm_to_json is in path
sys.path.append(os.path.dirname(__file__))  # Add backend/src

# Correct imports
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.config import GroupConfig, ReportConfig, ReportLayout, TextStyle
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.renderer import PDFRenderer


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

def inspect_data_step_by_step(table_data):
    print("\n--- STEP 1: Raw Table Inspection ---")
    for tname in ["Meet", "Session", "Sessitem", "Event", "Entry", "Relay", "Athlete"]:
        rows = table_data.get(tname, [])
        # Also check case variants
        if not rows:
            rows = table_data.get(tname.upper(), [])
        print(f"Table '{tname}': {len(rows)} rows found.")
        if rows:
            print(f"  First row keys: {list(rows[0].keys())}")

    print("\n--- STEP 2: Converter Inspection ---")
    converter = MmToJsonConverter(table_data=table_data)
    converted_data = converter.convert()
    sessions = converted_data.get("sessions", [])
    print(f"Converted Sessions: {len(sessions)}")
    
    total_events = 0
    total_entries = 0
    for i, sess in enumerate(sessions):
        evts = sess.get("events", [])
        total_events += len(evts)
        sess_entries = sum(len(e.get("entries", [])) for e in evts)
        total_entries += sess_entries
        print(f"  Session {i+1}: {len(evts)} events, {sess_entries} entries total")
    
    print(f"Total Converted: {total_events} events, {total_entries} entries")

    print("\n--- STEP 3: Extractor Inspection ---")
    extractor = ReportDataExtractor(converter)
    
    # Meet Program
    program_data = extractor.extract_meet_program_data()
    groups = program_data.get("groups", [])
    print(f"Extracted Meet Program: {len(groups)} groups (events)")
    if groups:
        first_group = groups[0]
        items = first_group.get("items", [])
        print(f"  Group 1 '{first_group.get('header')}': {len(items)} items (heats)")
        if items:
            sub_items = items[0].get("sub_items", [])
            print(f"    Heat 1: {len(sub_items)} entries")

    # Entries
    entries_data = extractor.extract_meet_entries_data()
    e_groups = entries_data.get("groups", [])
    print(f"Extracted Meet Entries: {len(e_groups)} groups (teams)")
    if e_groups:
        first_team = e_groups[0]
        athletes = first_team.get("items", [])
        print(f"  Group 1 '{first_team.get('header')}': {len(athletes)} athletes/relays")

    return converter, extractor

def verify_report_generation():
    # 1. Load Data
    data_path = "data/sample_data_champs_2025-aftermeet.mdb"
    if not os.path.exists(data_path):
        data_path = "../data/sample_data_champs_2025-aftermeet.mdb"
        if not os.path.exists(data_path):
            print(f"Error: {data_path} not found.")
            return

    print(f"Loading MDB from {data_path}...")
    table_data = load_mdb(data_path)
    
    # 2. Inspect intermediate steps
    converter, extractor = inspect_data_step_by_step(table_data)

    # 3. Render Example Reports
    print("\n--- STEP 4: Rendering PDFs ---")
    output_dir = "data/example_reports"
    if not os.path.exists(output_dir):
        output_dir = "../data/example_reports"
        os.makedirs(output_dir, exist_ok=True)

    # Meet Program
    print("Generating Meet Program...")
    program_data = extractor.extract_meet_program_data()
    from mm_to_json.reporting.report_definitions import MEET_PROGRAM_CONFIG
    prog_path = os.path.join(output_dir, "verify_champs_program.pdf")
    renderer = PDFRenderer(prog_path, MEET_PROGRAM_CONFIG)
    
    # Verification: Inspect elements before rendering
    elements = renderer._build_elements(program_data, 500)
    tables = [e for e in elements if hasattr(e, '__class__') and e.__class__.__name__ == 'Table']
    print(f"  Internal Verification: Found {len(elements)} elements and {len(tables)} data tables.")
    if len(tables) == 0:
        print("  ERROR: No data tables built! Report would be empty.")
    
    renderer.render(program_data)
    print(f"  Saved to {prog_path} ({os.path.getsize(prog_path) / 1024:.1f} KB)")

    # Results
    print("Generating Meet Results...")
    results_data = extractor.extract_results_data()
    from mm_to_json.reporting.report_definitions import RESULTS_REPORT_CONFIG
    res_path = os.path.join(output_dir, "verify_champs_results.pdf")
    PDFRenderer(res_path, RESULTS_REPORT_CONFIG).render(results_data)
    print(f"  Saved to {res_path} ({os.path.getsize(res_path) / 1024:.1f} KB)")

    print("\nDone!")

if __name__ == "__main__":
    verify_report_generation()
