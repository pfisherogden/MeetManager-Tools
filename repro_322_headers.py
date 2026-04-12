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
    
    # Ensure we have a relay event for testing
    # (Just assume sample data has some for now, or we'll see)

    # Convert
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    
    # Inject a mock relay event for verification
    mock_relay_event = {
        "eventNum": "99",
        "eventDesc": "Boys 8 & Under 100 Freestyle Relay",
        "isRelay": True,
        "entries": [
            {
                "heat": 1,
                "lane": 1,
                "team": "TEST",
                "relayLtr": "A",
                "time": "1:23.45",
                "is_relay": True,
                "swimmers": ["Swimmer 1", "Swimmer 2", "Swimmer 3", "Swimmer 4"]
            }
        ]
    }
    if "sessions" in full_data and full_data["sessions"]:
        full_data["sessions"][0]["events"].append(mock_relay_event)
    else:
        full_data["sessions"] = [{"events": [mock_relay_event]}]
    
    # Extract for Meet Program
    extractor = ReportDataExtractor(converter, full_data)
    extracted_data = extractor.extract_meet_program_data(show_dq_lines=True)
    
    # Setup Jinja Environment
    template_dir = "backend/src/mm_to_json/reporting/templates"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    
    # Render template
    template = env.get_template("meet_program.j2")
    
    render_context = {
        **extracted_data,
        "title": "S&T Judges Program",
        "generated_at": "2026-04-12",
        "generation_time": "05:00 PM 2026/04/12",
        "zebra_striping": True,
        "columns_on_page": 2,
        "show_dq_lines": True
    }
    
    with open(os.path.join(template_dir, "report_style.css"), "r") as f:
        render_context["css_content"] = f.read()
    
    html = template.render(**render_context)
    
    output_path = "verify_322_headers.html"
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Header verification HTML saved to {output_path}")

if __name__ == "__main__":
    generate_repro_html()
