import json
import os
import sys
import time
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer
from mm_to_json.reporting.playwright_renderer import PlaywrightRenderer

def run_benchmark():
    # Load sample data (Large dataset)
    sample_path = "data/fixtures_root/anonymized_meets/sample_data_champs_2025-aftermeet.json"
    if not os.path.exists(sample_path):
        sample_path = "backend/data/fixtures_root/anonymized_meets/sample_data_champs_2025-aftermeet.json"
    
    with open(sample_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    cache = fixture_wrapper["data"]
    
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    
    extractor = ReportDataExtractor(converter, full_data)
    prog_data = extractor.extract_meet_program_data(show_dq_lines=True)
    
    print(f"--- Starting Renderer Benchmark ({len(prog_data['groups'])} events) ---")
    
    # 1. WeasyPrint
    weasy = WeasyRenderer("bench_weasy.pdf")
    start = time.time()
    weasy.render_meet_program(prog_data)
    weasy_duration = time.time() - start
    print(f"WeasyPrint rendering: {weasy_duration:.2f}s")

    # 2. Playwright
    try:
        pw = PlaywrightRenderer("bench_playwright.pdf")
        start = time.time()
        pw.render_meet_program(prog_data)
        pw_duration = time.time() - start
        print(f"Playwright rendering: {pw_duration:.2f}s")
        
        improvement = (weasy_duration - pw_duration) / weasy_duration * 100
        print(f"Playwright Speedup: {weasy_duration / pw_duration:.1f}x ({improvement:.1f}% faster)")
        
        weasy_size = os.path.getsize("bench_weasy.pdf") / 1024
        pw_size = os.path.getsize("bench_playwright.pdf") / 1024
        print(f"File Size - WeasyPrint: {weasy_size:.1f} KB, Playwright: {pw_size:.1f} KB")
        print(f"File Size Increase: {pw_size / weasy_size:.1f}x")
        
    except Exception as e:
        print(f"Playwright failed: {e}")
        print("Make sure to run 'pip install playwright && playwright install chromium' first.")

if __name__ == "__main__":
    run_benchmark()
