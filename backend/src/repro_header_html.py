
import json
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

def generate_repro_html():
    logging.basicConfig(level=logging.ERROR)
    
    # 1. Load sample data
    fixture_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json"))
    with open(fixture_path, 'r') as f:
        data = json.load(f)
    
    # 2. Convert and Extract
    converter = MmToJsonConverter(table_data=data)
    extractor = ReportDataExtractor(converter)
    
    # Generate Meet Program data (reported as broken too)
    report_data = extractor.extract_meet_program_data()
    
    # 3. Render to HTML
    renderer = WeasyRenderer("dummy.pdf")
    # For visual inspection, we want to see the header clearly
    # We'll use a template that includes the base report
    html = renderer.render_to_html(report_data, "meet_program.j2")
    
    # 4. Save HTML for screenshotting
    output_path = "repro_header.html"
    with open(output_path, "w") as f:
        f.write(html)
    print(f"HTML saved to: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    generate_repro_html()
