import json
import os
import sys
import tempfile

# Add backend/src to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(repo_root, 'backend', 'src'))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.renderer import PDFRenderer
from mm_to_json.reporting.report_definitions import MEET_PROGRAM_CONFIG

def test_report_from_fixture():
    fixture_path = os.path.join(repo_root, "tests/fixtures/anonymized_champs.json")
    with open(fixture_path, 'r') as f:
        payload = json.load(f)
        table_data = payload.get("data", payload)

    print(f"Loading data from {fixture_path}...")
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    print("Extracting Meet Program data...")
    program_data = extractor.extract_meet_program_data()
    groups = program_data.get("groups", [])
    print(f"Extracted {len(groups)} groups.")
    
    if not groups:
        print("ERROR: No groups extracted!")
        return False

    # Check for items in the first group
    first_group = groups[0]
    items = first_group.get("items", [])
    print(f"Group 1 '{first_group.get('header')}' has {len(items)} items (heats).")
    
    if not items:
        print("ERROR: First group has no items!")
        return False

    output_pdf = os.path.join(repo_root, "backend/data/example_reports/test_anonymized_program.pdf")
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    
    print(f"Rendering PDF to {output_pdf}...")
    renderer = PDFRenderer(output_pdf, MEET_PROGRAM_CONFIG)
    
    # Internal verification of built elements
    elements = renderer._build_elements(program_data, 500)
    tables = [e for e in elements if hasattr(e, '__class__') and e.__class__.__name__ == 'Table']
    print(f"Internal Verification: Built {len(elements)} elements, including {len(tables)} data tables.")
    
    if len(tables) < 10: # We expect many tables for a full meet
        print(f"ERROR: Too few tables ({len(tables)}). Report likely missing body data.")
        return False

    renderer.render(program_data)
    print(f"SUCCESS: Report generated and verified. Size: {os.path.getsize(output_pdf) / 1024:.1f} KB")
    return True

if __name__ == "__main__":
    if test_report_from_fixture():
        sys.exit(0)
    else:
        sys.exit(1)
