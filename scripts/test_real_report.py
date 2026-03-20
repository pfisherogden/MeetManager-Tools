import os
import sys
import json
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer
from bs4 import BeautifulSoup

def test_real_report():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixture_path = os.path.join(base_dir, "tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json")
    
    if not os.path.exists(fixture_path):
        print(f"Fixture not found at {fixture_path}")
        return

    print(f"Loading Fixture: {fixture_path}")
    with open(fixture_path, 'r') as f:
        cache_raw = json.load(f)
    
    # Mirror server.py logic
    cache_data = cache_raw.get("data", cache_raw)
    cache = {k.lower(): v for k, v in cache_data.items()}

    converter = MmToJsonConverter(table_data=cache)
    extractor = ReportDataExtractor(converter)
    
    print("Extracting meet program data...")
    # Test with default settings (Mixed gender, all teams)
    data = extractor.extract_meet_program_data()
    
    print(f"Extraction complete. Groups found: {len(data.get('groups', []))}")
    
    if len(data.get('groups', [])) == 0:
        print("❌ FAILURE: Groups list is empty!")
        return

    # Verify first group entries
    first_group = data['groups'][0]
    total_entries = 0
    for heat in first_group.get('heats', []):
        total_entries += len(heat.get('sub_items', []))
    
    print(f"First group '{first_group['header']}' has {total_entries} entries.")
    
    if total_entries == 0:
        print("❌ FAILURE: First group has no entries!")
        return

    # Render to HTML
    print("Rendering to HTML...")
    output_pdf = "test_output.pdf"
    renderer = WeasyRenderer(output_pdf)
    html = renderer.render_to_html(data)
    
    soup = BeautifulSoup(html, "html.parser")
    entry_rows = soup.find_all("tr", class_="entry-row")
    print(f"HTML rendering complete. Found {len(entry_rows)} entry rows in HTML.")
    
    if len(entry_rows) == 0:
        print("❌ FAILURE: No entry rows found in rendered HTML!")
        # Print a snippet of HTML for debugging
        content_div = soup.find("div", class_="content-container")
        print("\nContent Container snippet:")
        print(str(content_div)[:500])
        return

    print("✅ SUCCESS: Report has data.")

if __name__ == "__main__":
    # Ensure we are in backend/src context
    os.chdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend/src"))
    sys.path.append(os.getcwd())
    test_real_report()
