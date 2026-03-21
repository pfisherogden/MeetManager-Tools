import json
import os
import sys

# Ensure mm_to_json is in path
sys.path.append(os.path.dirname(__file__))  # Add backend/src

# Correct imports
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.renderer import PDFRenderer


def inspect_data_step_by_step(table_data):
    print("\n--- STEP 1: Raw Table Inspection ---")
    # Tables we care about for linking
    for tname in ["Meet", "Session", "Sessitem", "Event", "Entry", "Relay", "Athlete", "Team"]:
        rows = table_data.get(tname, [])
        # Also check case variants
        if not rows:
            for k in table_data.keys():
                if k.lower() == tname.lower():
                    rows = table_data[k]
                    break
        print(f"Table '{tname}': {len(rows)} rows found.")
        if rows and len(rows) > 0 and tname == "Team":
            print(f"  Team Names: {[r.get('team_name') or r.get('Team_name') for r in rows]}")

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

    # Meet Program (No Filter)
    program_data = extractor.extract_meet_program_data()
    print(f"Extracted Meet Program (No Filter): {len(program_data.get('groups', []))} groups")

    # Meet Program (Filtered - should use the new robust logic)
    # Based on anonymized data, we might have "Blue Dolphins"
    target_team = "Blue Dolphins"
    program_data_filtered = extractor.extract_meet_program_data(team_filter=target_team)
    print(f"Extracted Meet Program (Filter: {target_team}): {len(program_data_filtered.get('groups', []))} groups")

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
    with open(json_path, "r") as f:
        table_data = json.load(f)

    # 2. Inspect intermediate steps
    converter, extractor = inspect_data_step_by_step(table_data)

    # 3. Render Example Reports
    print("\n--- STEP 4: Rendering PDFs (with visual improvements) ---")
    output_dir = "../repro_reports"
    os.makedirs(output_dir, exist_ok=True)

    from mm_to_json.reporting.report_definitions import MEET_PROGRAM_CONFIG, PSYCH_SHEET_CONFIG

    # Use a helper to render both weasy and legacy if needed
    def render_and_save(data, config, filename, title):
        print(f"Generating {title}...")
        path = os.path.join(output_dir, filename)
        
        # Try WeasyRenderer first (this is what Cloud Run uses)
        try:
            from mm_to_json.reporting.weasy_renderer import WeasyRenderer
            print(f"  Attempting WeasyRenderer for {filename}...")
            renderer = WeasyRenderer(path)
            if "Program" in title:
                renderer.render_meet_program(data)
            else:
                renderer.render_entries(data, "psych_sheet.j2")
            print(f"  SUCCESS (Weasy): Saved to {path} ({os.path.getsize(path) / 1024:.1f} KB)")
        except Exception as e:
            print(f"  WeasyRenderer failed: {e}")
            print(f"  Falling back to legacy PDFRenderer for {filename}...")
            from mm_to_json.reporting.renderer import PDFRenderer
            legacy_renderer = PDFRenderer(path, config)
            legacy_renderer.render(data)
            print(f"  SUCCESS (Legacy): Saved to {path} ({os.path.getsize(path) / 1024:.1f} KB)")

    # 1. Full Meet Program
    prog_data = extractor.extract_meet_program_data(report_title="Full Meet Program - Visual Test")
    render_and_save(prog_data, MEET_PROGRAM_CONFIG, "visual_full_program.pdf", "Full Program")

    # 2. Filtered Meet Program
    target = "Blue Dolphins"
    filtered_prog = extractor.extract_meet_program_data(team_filter=target, report_title=f"Program - {target}")
    render_and_save(filtered_prog, MEET_PROGRAM_CONFIG, "visual_filtered_program.pdf", f"Filtered Program ({target})")

    # 3. Psych Sheet
    psych_data = extractor.extract_psych_sheet_data(report_title="Psych Sheet - Visual Test")
    render_and_save(psych_data, PSYCH_SHEET_CONFIG, "visual_psych_sheet.pdf", "Psych Sheet")

    print("\nReproduction and Visual Test complete.")


if __name__ == "__main__":
    repro_empty_reports()
