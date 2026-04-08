import os
import json
import tempfile
import sys
import logging

# Ensure macOS libraries are found if running locally
if os.name == "posix" and "darwin" in sys.platform:
    if "/opt/homebrew/lib" not in os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", ""):
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib:" + os.environ.get(
            "DYLD_FALLBACK_LIBRARY_PATH", ""
        )

# Add backend/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend/src")))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

def test_full_meet_program_rendering():
    """
    Local reproduction for Issue #292: WeasyPrint crash in 2-column layout.
    """
    logging.basicConfig(level=logging.INFO)
    
    # Load sample data
    sample_path = "backend/data/Sample_Data.json"
    with open(sample_path, "r") as f:
        table_data = json.load(f)

    converter = MmToJsonConverter(table_data=table_data)
    # Perform full conversion
    full_data = converter.convert()
    extractor = ReportDataExtractor(converter, full_data=full_data)

    # 1. Verify 2-column layout (Previously crashed)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        output_path = tmp.name
    
    try:
        renderer = WeasyRenderer(output_path)
        # Extract program for all teams
        program_data = extractor.extract_meet_program_data(columns_on_page=2)
        
        print(f"DEBUG: Groups extracted: {len(program_data.get('groups', []))}")
        assert len(program_data.get('groups', [])) > 0
        
        print("Starting WeasyPrint rendering (2 columns)...")
        renderer.render_meet_program(program_data)
        print(f"SUCCESS: Rendered 2-column PDF to {output_path}")
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

    # 2. Verify Team Filtering (Previously might result in empty report)
    # Get a real team name
    raw_teams = converter.tables.get("team")
    if not raw_teams.empty:
        first_row = raw_teams.iloc[0]
        team_name = str(first_row.get("team_name") or first_row.get("name") or "")
        print(f"Testing filter for team: {team_name}")
        
        filtered_data = extractor.extract_meet_program_data(team_filter=team_name)
        num_events = len(filtered_data.get("groups", []))
        print(f"Extracted {num_events} events for team {team_name}")
        assert num_events > 0, f"Expected events for team {team_name}, got 0"

if __name__ == "__main__":
    try:
        test_full_meet_program_rendering()
        print("\nALL REPRODUCTION TESTS PASSED!")
    except Exception as e:
        print(f"\nREPRODUCTION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
