
import json
import os
import sys
import logging
from weasyprint import HTML

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

def reproduce_issue():
    # Set logging to catch WeasyPrint warnings
    logger = logging.getLogger('weasyprint')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    
    # 1. Load sample data
    fixture_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json"))
    with open(fixture_path, 'r') as f:
        data = json.load(f)
    
    # 2. Convert and Extract
    converter = MmToJsonConverter(table_data=data)
    extractor = ReportDataExtractor(converter)
    report_data = extractor.extract_lane_timer_sheets_data()
    
    # 3. Render to HTML
    renderer = WeasyRenderer("dummy.pdf")
    html = renderer.render_to_html(report_data, "timer_sheets.j2")
    
    # 4. Generate PDF and check logs
    print("GENERATING PDF WITH WEASYPRINT...")
    HTML(string=html).write_pdf("repro_output.pdf")
    print("DONE.")

if __name__ == "__main__":
    reproduce_issue()
