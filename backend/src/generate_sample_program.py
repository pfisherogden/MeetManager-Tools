
import json
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

def generate_sample_report():
    logging.basicConfig(level=logging.ERROR)
    
    # 1. Load large sample data (champs)
    fixture_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tests/fixtures/anonymized_champs.json"))
    with open(fixture_path, 'r') as f:
        data = json.load(f)
    
    table_data = data.get("data", data)
    
    # 2. Convert and Extract
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    # Generate Meet Program data
    report_data = extractor.extract_meet_program_data()
    
    # 3. Render to HTML
    renderer = WeasyRenderer("sample_meet_program.pdf")
    html = renderer.render_to_html(report_data, "meet_program.j2")
    
    # 4. Save HTML for inspection
    output_html = "sample_meet_program.html"
    with open(output_html, "w") as f:
        f.write(html)
    print(f"Sample HTML saved to: {os.path.abspath(output_html)}")
    
    # 5. Generate PDF (if possible)
    try:
        renderer.render_meet_program(report_data)
        print(f"Sample PDF saved to: {os.path.abspath('sample_meet_program.pdf')}")
    except Exception as e:
        print(f"PDF generation failed: {e}")

if __name__ == "__main__":
    generate_sample_report()
