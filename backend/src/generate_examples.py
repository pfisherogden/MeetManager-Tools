import copy
import logging
import os
import sys

from weasyprint import HTML

sys.path.insert(0, "/app/src")

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

logging.basicConfig(level=logging.INFO)

def generate_examples():
    os.makedirs("/app/src/examples", exist_ok=True)
    
    sample_mdb = "/app/data/sample_data_champs_2025-aftermeet.mdb"
    print(f"Loading data from '{sample_mdb}'...")
    converter = MmToJsonConverter(sample_mdb)
    extractor = ReportDataExtractor(converter)
    
    print("Generating Meet Program (1-Column)...")
    program_data_1col = extractor.extract_meet_program_data(columns_on_page=1)
    WeasyRenderer("/app/src/examples/example_meet_program_1col.pdf").render_meet_program(program_data_1col)
    
    print("Generating Meet Program (2-Column)...")
    program_data_2col = extractor.extract_meet_program_data(columns_on_page=2)
    WeasyRenderer("/app/src/examples/example_meet_program_2col.pdf").render_meet_program(program_data_2col)
    # Compatibility link
    WeasyRenderer("/app/src/examples/example_meet_program.pdf").render_meet_program(program_data_2col)
    
    print("Generating S&T Judge Report (1-Column with DQ Lines)...")
    st_data = extractor.extract_meet_program_data(columns_on_page=1, show_dq_lines=True, report_title="Stroke & Turn Judge Report", show_relay_swimmers=True)
    WeasyRenderer("/app/src/examples/example_st_judge_report.pdf").render_meet_program(st_data)
    
    print("Generating Timer Sheets...")
    timer_data = extractor.extract_timer_sheets_data(lane_filter=1)
    WeasyRenderer("/app/src/examples/example_timer_sheets.pdf").render_entries(timer_data, "timer_sheets.j2")
    
    print("\nExample reports generated in '/app/src/examples'")

if __name__ == "__main__":
    generate_examples()
