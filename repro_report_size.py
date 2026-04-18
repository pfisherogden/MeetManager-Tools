import json
import os
import sys
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def test_report_sizes():
    # Load sample data
    sample_path = "data/fixtures_root/anonymized_meets/sample_data_champs_2025-aftermeet.json"
    if not os.path.exists(sample_path):
        sample_path = "tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json"
        
    with open(sample_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    cache = fixture_wrapper["data"]
    
    # Convert
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    
    # Setup Jinja Environment
    template_dir = "src/mm_to_json/reporting/templates"
    if not os.path.exists(template_dir):
        template_dir = "backend/src/mm_to_json/reporting/templates"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("meet_program.j2")
    
    # CSS
    with open(os.path.join(template_dir, "report_style.css"), "r") as f:
        css_content = f.read()

    # 1. Generate Meet Program
    extractor = ReportDataExtractor(converter, full_data)
    prog_data = extractor.extract_meet_program_data(show_dq_lines=False)
    prog_context = {
        **prog_data,
        "title": "Meet Program",
        "generated_at": "2026-04-12",
        "generation_time": "05:00 PM 2026/04/12",
        "zebra_striping": True,
        "columns_on_page": 2,
        "show_dq_lines": False,
        "css_content": css_content
    }
    prog_html = template.render(**prog_context)
    prog_doc = HTML(string=prog_html).render()
    prog_doc.write_pdf("test_meet_program.pdf")
    prog_size = os.path.getsize("test_meet_program.pdf") / 1024
    print(f"Meet Program: {prog_size:.2f} KB, Pages: {len(prog_doc.pages)}")

    # 2. Generate S&T Judges Report
    judge_data = extractor.extract_meet_program_data(show_dq_lines=True)
    judge_context = {
        **judge_data,
        "title": "S&T Judges Program",
        "generated_at": "2026-04-12",
        "generation_time": "05:00 PM 2026/04/12",
        "zebra_striping": True,
        "columns_on_page": 2,
        "show_dq_lines": True,
        "css_content": css_content
    }
    judge_html = template.render(**judge_context)
    judge_doc = HTML(string=judge_html).render()
    judge_doc.write_pdf("test_judge_sheets.pdf")
    judge_size = os.path.getsize("test_judge_sheets.pdf") / 1024
    print(f"Judge Sheets: {judge_size:.2f} KB, Pages: {len(judge_doc.pages)}")

    # 3. Lane Timer Sheets
    template = env.get_template("timer_sheets.j2")
    timer_data = extractor.extract_lane_timer_sheets_data()
    timer_context = {
        **timer_data,
        "css_content": css_content,
        "generation_time": "05:00 PM 2026/04/12",
    }
    timer_html = template.render(**timer_context)
    timer_doc = HTML(string=timer_html).render()
    timer_doc.write_pdf("test_lane_timer_sheets.pdf")
    timer_size = os.path.getsize("test_lane_timer_sheets.pdf") / 1024
    print(f"Lane Timer Sheets: {timer_size:.2f} KB, Pages: {len(timer_doc.pages)}")

if __name__ == "__main__":
    test_report_sizes()
