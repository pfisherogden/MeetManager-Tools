import json
import os
import sys
import time
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer
from mm_to_json.reporting.playwright_renderer import PlaywrightRenderer

def generate_comparisons():
    # Load sample data (Large dataset)
    sample_path = "data/fixtures_root/anonymized_meets/sample_data_champs_2025-aftermeet.json"
    if not os.path.exists(sample_path):
        sample_path = "backend/data/fixtures_root/anonymized_meets/sample_data_champs_2025-aftermeet.json"
    
    with open(sample_path, "r") as f:
        fixture_wrapper = json.load(f)
    cache = fixture_wrapper["data"]
    
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    extractor = ReportDataExtractor(converter, full_data)

    reports_to_test = [
        {"type": "program", "name": "Meet Program", "method": extractor.extract_meet_program_data, "args": {"show_dq_lines": False}},
        {"type": "judge_sheets", "name": "Judge Sheets", "method": extractor.extract_meet_program_data, "args": {"show_dq_lines": True}},
        {"type": "timer_sheets", "name": "Lane Timer Sheets", "method": extractor.extract_lane_timer_sheets_data, "args": {}},
        {"type": "psych", "name": "Psych Sheet", "method": extractor.extract_psych_sheet_data, "args": {}},
        {"type": "entries", "name": "Entries", "method": extractor.extract_meet_entries_data, "args": {}},
        {"type": "results", "name": "Results", "method": extractor.extract_results_data, "args": {}},
    ]

    results = []

    for report in reports_to_test:
        print(f"\nProcessing {report['name']}...")
        data = report["method"](**report["args"])
        
        # 1. WeasyPrint
        weasy_path = f"comp_weasy_{report['type']}.pdf"
        weasy = WeasyRenderer(weasy_path)
        start = time.time()
        if report["type"] == "program" or report["type"] == "judge_sheets":
            weasy.render_meet_program(data)
        else:
            # Most others use the base render_entries with a specific template
            template_map = {
                "timer_sheets": "timer_sheets.j2",
                "psych": "psych_sheet.j2",
                "entries": "entries_club.j2",
                "results": "results.j2"
            }
            weasy.render_entries(data, template_map.get(report["type"], "meet_program.j2"))
        weasy_duration = time.time() - start

        # 2. Playwright
        pw_path = f"comp_playwright_{report['type']}.pdf"
        pw = PlaywrightRenderer(pw_path)
        start = time.time()
        if report["type"] == "program" or report["type"] == "judge_sheets":
            pw.render_meet_program(data)
        else:
            template_map = {
                "timer_sheets": "timer_sheets.j2",
                "psych": "psych_sheet.j2",
                "entries": "entries_club.j2",
                "results": "results.j2"
            }
            pw.render_entries(data, template_map.get(report["type"], "meet_program.j2"))
        pw_duration = time.time() - start

        print(f"  WeasyPrint: {weasy_duration:.2f}s")
        print(f"  Playwright: {pw_duration:.2f}s ({weasy_duration/pw_duration:.1f}x speedup)")
        
        results.append({
            "report": report["name"],
            "weasy_time": weasy_duration,
            "pw_time": pw_duration,
            "speedup": weasy_duration / pw_duration
        })

    print("\n--- Summary ---")
    for r in results:
        print(f"{r['report']}: {r['speedup']:.1f}x faster")

if __name__ == "__main__":
    generate_comparisons()
