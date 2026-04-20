import json
import os
import sys
import time

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


def run_benchmark():
    # Load sample data (Large dataset)
    sample_path = "data/fixtures_root/anonymized_meets/sample_data_champs_2025-aftermeet.json"
    if not os.path.exists(sample_path):
        sample_path = "backend/data/fixtures_root/anonymized_meets/sample_data_champs_2025-aftermeet.json"

    with open(sample_path) as f:
        fixture_wrapper = json.load(f)

    cache = fixture_wrapper["data"]

    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    template_dir = "mm_to_json/reporting/templates"
    if not os.path.exists(template_dir):
        template_dir = "src/mm_to_json/reporting/templates"

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("meet_program.j2")
    with open(os.path.join(template_dir, "report_style.css")) as f:
        css_content = f.read()

    extractor = ReportDataExtractor(converter, full_data)
    prog_data = extractor.extract_meet_program_data(show_dq_lines=True)
    prog_context = {
        **prog_data,
        "title": "Benchmark Program",
        "generation_time": "05:00 PM 2026/04/12",
        "zebra_striping": True,
        "columns_on_page": 2,
        "show_dq_lines": True,
        "css_content": css_content
    }
    html_out = template.render(**prog_context)

    print(f"--- Starting WeasyPrint Benchmark ({len(prog_data['groups'])} events) ---")

    # Warm-up render
    HTML(string=html_out).write_pdf("/tmp/warmup.pdf")

    iterations = 3

    # 1. Unoptimized
    unoptimized_times = []
    for i in range(iterations):
        start = time.time()
        HTML(string=html_out).write_pdf(f"/tmp/bench_unreg_{i}.pdf")
        unoptimized_times.append(time.time() - start)

    avg_unoptimized = sum(unoptimized_times) / iterations
    print(f"Avg Unoptimized: {avg_unoptimized:.2f}s")

    # 2. Optimized (No font subsetting)
    optimized_times = []
    for i in range(iterations):
        start = time.time()
        HTML(string=html_out).write_pdf(f"/tmp/bench_opt_{i}.pdf", optimize_size=("images",))
        optimized_times.append(time.time() - start)

    avg_optimized = sum(optimized_times) / iterations
    print(f"Avg Optimized (no font subsetting): {avg_optimized:.2f}s")

    improvement = (avg_unoptimized - avg_optimized) / avg_unoptimized * 100
    print(f"Net Improvement: {improvement:.1f}%")

    # Cleanup
    if os.path.exists("bench_unoptimized.pdf"): os.remove("bench_unoptimized.pdf")
    if os.path.exists("bench_optimized.pdf"): os.remove("bench_optimized.pdf")

if __name__ == "__main__":
    run_benchmark()
