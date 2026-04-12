import json
import os
import sys
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def generate_repro_html():
    # Load sample data
    sample_path = "backend/data/Sample_Data.json"
    with open(sample_path, "r") as f:
        cache = json.load(f)
    
    # Convert
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    
    # Extract for Meet Program (Type 4)
    extractor = ReportDataExtractor(converter, full_data)
    # Using extract_meet_program_data
    extracted_data = extractor.extract_meet_program_data(
        show_dq_lines=True
    )
    
    # Setup Jinja Environment
    template_dir = "backend/src/mm_to_json/reporting/templates"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    
    # Render template
    template_name = "meet_program.j2"
    template = env.get_template(template_name)
    
    # Add common helpers used in templates
    render_context = {
        **extracted_data,
        "title": "S&T Judges Program",
        "generated_at": "2026-04-12",
        "generation_time": "04:59 PM 2026/04/12",
        "zebra_striping": True,
        "columns_on_page": 2,
        "show_dq_lines": True
    }
    
    # Read CSS for injection
    css_path = os.path.join(template_dir, "report_style.css")
    with open(css_path, "r") as f:
        css_content = f.read()
    render_context["css_content"] = css_content
    
    html = template.render(**render_context)
    
    output_path = "repro_317_layout.html"
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Reproduction HTML saved to {output_path}")

if __name__ == "__main__":
    generate_repro_html()
