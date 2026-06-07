import logging
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.playwright_renderer import PlaywrightRenderer

def run_audit():
    # Use a real MDB for testing
    mdb_path = "/Users/pfo/Developer/tmp/2026_meet1_final.mdb"
    if not os.path.exists(mdb_path):
        print(f"Error: {mdb_path} not found")
        return

    converter = MmToJsonConverter(mdb_path)
    data = converter.convert()
    
    extractor = ReportDataExtractor(converter, data)
    
    # 1. Girls Lineup (Check mixed inclusion and header alignment)
    print("Generating Girls Lineup Audit (DP Team Filter)...")
    girls_program_dp = extractor.extract_meet_program_data(
        team_filter="DP",
        gender_filter="Girls", 
        report_title="Girls Lineup Audit DP",
        columns_on_page=2
    )
    renderer_dp = PlaywrightRenderer("girls_lineup_dp_audit.pdf")
    renderer_dp.render_meet_program(girls_program_dp)
    
    mixed_events_dp = [g["header"] for g in girls_program_dp["groups"] if "Mixed" in g["header"]]
    print(f"Found {len(mixed_events_dp)} Mixed events in Girls Lineup (DP Filter)")

    print("\nGenerating Girls Lineup Audit (FAST Team Filter)...")
    girls_program_fast = extractor.extract_meet_program_data(
        team_filter="FAST",
        gender_filter="Girls", 
        report_title="Girls Lineup Audit FAST",
        columns_on_page=2
    )
    renderer_fast = PlaywrightRenderer("girls_lineup_fast_audit.pdf")
    renderer_fast.render_meet_program(girls_program_fast)
    
    mixed_events_fast = [g["header"] for g in girls_program_fast["groups"] if "Mixed" in g["header"]]
    print(f"Found {len(mixed_events_fast)} Mixed events in Girls Lineup (FAST Filter)")
    for me in mixed_events_fast:
        print(f"  - {me}")

    # 2. Results (Check header alignment)
    print("\nGenerating Results Audit...")
    results_data = extractor.extract_results_data(
        report_title="Full Results Audit"
    )
    renderer_res = PlaywrightRenderer("results_audit.pdf")
    renderer_res.render_entries(results_data, "results.j2")

    print("\nAudit PDFs generated: girls_lineup_dp_audit.pdf, results_audit.pdf")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_audit()
