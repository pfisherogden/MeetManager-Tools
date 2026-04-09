import json
import os
import sys
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def test_lane_timer_sheets_html():
    # Load sample data
    sample_path = "backend/data/Sample_Data.json"
    with open(sample_path, "r") as f:
        cache = json.load(f)
    
    # Convert
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    
    # Extract for Lane Timer Sheets (Type 8)
    extractor = ReportDataExtractor(converter, full_data)
    # Use extract_lane_timer_sheets_data for Type 8
    extracted_data = extractor.extract_lane_timer_sheets_data()
    
    # Setup Jinja Environment
    template_dir = "backend/src/mm_to_json/reporting/templates"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    
    # Render template
    template_name = "timer_sheets.j2"
    template = env.get_template(template_name)
    
    # Add common helpers used in templates
    # The template expects 'groups'
    groups = extracted_data.get("groups", [])
    
    render_context = {
        "groups": groups,
        "title": "Lane Timer Sheets",
        "generated_at": "2026-04-09",
        "zebra_striping": True,
        "columns_on_page": 1
    }
    
    html = template.render(**render_context)
    
    if html:
        size_kb = len(html) / 1024
        print(f"SUCCESS: Generated Timer Sheets HTML. Size: {size_kb:.2f} KB")
        
        # Save locally for inspection
        output_path = "local_timer_sheets.html"
        with open(output_path, "w") as f:
            f.write(html)
        print(f"Saved to {output_path}")
        
        # Check for actual data rows
        heat_count = html.count("timer-row")
        print(f"INFO: Found {heat_count} data rows in HTML.")
        
        group_count = len(groups)
        print(f"INFO: Found {group_count} groups (lanes) in extracted data.")
        
        if heat_count == 0:
            print("WARNING: No data rows found in generated HTML!")
    else:
        print("FAILED: HTML generation returned empty result")

if __name__ == "__main__":
    test_lane_timer_sheets_html()
