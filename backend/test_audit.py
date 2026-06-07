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
    print("Generating Girls Lineup Audit...")
    girls_program = extractor.extract_meet_program_data(
        gender_filter="Girls", 
        report_title="Girls Lineup Audit",
        columns_on_page=2
    )
    renderer = PlaywrightRenderer("girls_lineup_audit.pdf")
    renderer.render_meet_program(girls_program)
    
    # 2. Results (Check margins and points alignment)
    print("Generating Results Audit...")
    results_data = extractor.extract_results_data(
        report_title="Full Results Audit"
    )
    renderer_res = PlaywrightRenderer("results_audit.pdf")
    renderer_res.render_entries(results_data, "results.j2")

    print("\nAudit PDFs generated: girls_lineup_audit.pdf, results_audit.pdf")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_audit()
