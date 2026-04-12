import json
import os
import sys
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def verify_long_name():
    # Load sample data
    sample_path = "backend/data/Sample_Data.json"
    with open(sample_path, "r") as f:
        cache = json.load(f)
    
    # Inject a very long name
    if "Athlete" in cache:
        for ath in cache["Athlete"]:
            # Overwrite all possible variants
            for k in ["Last_name", "last_name", "Last", "last"]:
                if k in ath: ath[k] = "Doppalapudi-Longname-Extremely-Long-Indeed-Very-Long"
            for k in ["First_name", "first_name", "First", "first"]:
                if k in ath: ath[k] = "Sahasra Deepika The Great"

    # Convert
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    
    # Extract
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
        "title": "Long Name Verification",
        "generated_at": "2026-04-12",
        "generation_time": "05:00 PM 2026/04/12",
        "zebra_striping": True,
        "columns_on_page": 2,
        "show_dq_lines": True
    }
    
    with open(os.path.join(template_dir, "report_style.css"), "r") as f:
        render_context["css_content"] = f.read()
    
    html = template.render(**render_context)
    
    output_path = "verify_313_long_name.html"
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Long name verification HTML saved to {output_path}")
    
    # Check if the long name is in the HTML
    if "Doppalapudi-Longname" in html:
        print("SUCCESS: Long name found in rendered HTML.")
    else:
        print("FAILURE: Long name NOT found in rendered HTML.")

if __name__ == "__main__":
    verify_long_name()
