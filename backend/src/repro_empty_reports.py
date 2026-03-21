import json
import os
import sys

# Ensure mm_to_json is in path
sys.path.append(os.path.dirname(__file__))  # Add backend/src

# Correct imports
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


def inspect_data_step_by_step(table_data):
    print("\n--- STEP 1: Raw Table Inspection ---")
    # Tables we care about for linking
    for tname in ["Meet", "Session", "Sessitem", "Event", "Entry", "Relay", "Athlete"]:
        rows = table_data.get(tname, [])
        # Also check case variants (MmToJsonConverter handles this but we want to see it here)
        if not rows:
            for k in table_data.keys():
                if k.lower() == tname.lower():
                    rows = table_data[k]
                    break
        print(f"Table '{tname}': {len(rows)} rows found.")
        if rows and len(rows) > 0:
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
        print(f"  Session {i + 1} '{sess.get('name')}': {len(evts)} events, {sess_entries} entries total")

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
    else:
        print("  WARNING: NO GROUPS EXTRACTED FOR MEET PROGRAM!")

    # Psych Sheet
    psych_data = extractor.extract_psych_sheet_data()
    p_groups = psych_data.get("groups", [])
    print(f"Extracted Psych Sheet: {len(p_groups)} groups (events)")
    if p_groups:
        print(f"  Group 1 '{p_groups[0].get('header')}': {len(p_groups[0].get('items', []))} entries")
    else:
        print("  WARNING: NO GROUPS EXTRACTED FOR PSYCH SHEET!")

    return converter, extractor


def repro_empty_reports():
    # 1. Load Anonymized Data
    json_path = "../tests/fixtures/anonymized_champs.json"
    if not os.path.exists(json_path):
        json_path = "tests/fixtures/anonymized_champs.json"
        if not os.path.exists(json_path):
            print(f"Error: {json_path} not found.")
            return

    print(f"Loading JSON from {json_path}...")
    with open(json_path) as f:
        table_data = json.load(f)

    # 2. Inspect intermediate steps
    converter, extractor = inspect_data_step_by_step(table_data)

    # 3. Render Example Reports
    print("\n--- STEP 4: Rendering PDFs ---")
    output_dir = "../repro_reports"
    os.makedirs(output_dir, exist_ok=True)

    # Meet Program
    print("Generating Meet Program...")
    program_data = extractor.extract_meet_program_data()
    from mm_to_json.reporting.report_definitions import MEET_PROGRAM_CONFIG

    prog_path = os.path.join(output_dir, "repro_champs_program.pdf")
    # Wrap in try-except to catch WeasyPrint errors if libraries missing
    try:
        from mm_to_json.reporting.weasy_renderer import WeasyRenderer

        print("Using WeasyRenderer (HTML-based)...")
        renderer = WeasyRenderer(prog_path)
        renderer.render_meet_program(program_data)
        print(f"  Saved to {prog_path} ({os.path.getsize(prog_path) / 1024:.1f} KB)")
    except Exception as e:
        print(f"WeasyRenderer failed: {e}")
        print("Falling back to legacy PDFRenderer...")
        from mm_to_json.reporting.renderer import PDFRenderer

        legacy_renderer = PDFRenderer(prog_path, MEET_PROGRAM_CONFIG)
        legacy_renderer.render(program_data)
        print(f"  Saved to {prog_path} ({os.path.getsize(prog_path) / 1024:.1f} KB)")

    # Psych Sheet
    print("Generating Psych Sheet...")
    psych_data = extractor.extract_psych_sheet_data()
    from mm_to_json.reporting.report_definitions import PSYCH_SHEET_CONFIG

    p_path = os.path.join(output_dir, "repro_champs_psych.pdf")
    PDFRenderer(p_path, PSYCH_SHEET_CONFIG).render(psych_data)
    print(f"  Saved to {p_path} ({os.path.getsize(p_path) / 1024:.1f} KB)")

    print("\nReproduction check complete.")


if __name__ == "__main__":
    repro_empty_reports()
