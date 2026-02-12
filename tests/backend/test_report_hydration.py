import os
import json
import pytest
import sys

# Add backend/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/src")))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../fixtures/anonymized_meets"))

def get_anonymized_fixtures():
    fixtures = []
    if os.path.exists(FIXTURES_DIR):
        for f in os.listdir(FIXTURES_DIR):
            if f.endswith(".json"):
                fixtures.append(os.path.join(FIXTURES_DIR, f))
    return fixtures

@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_report_data_extraction(fixture_path):
    with open(fixture_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    
    full_data = converter.convert()
    extractor = ReportDataExtractor(converter)
    
    # Test Meet Entries data extraction
    entries_data = extractor.extract_meet_entries_data()
    assert "meet_name" in entries_data
    assert "groups" in entries_data
    assert len(entries_data["groups"]) > 0
    
    for team in entries_data["groups"]:
        assert "header" in team
        assert "items" in team

    # Test Meet Program data extraction
    program_data = extractor.extract_meet_program_data()
    assert "meet_name" in program_data
    assert "groups" in program_data
    
    if "Session" in converter.tables and not converter.tables["Session"].empty:
        assert len(program_data["groups"]) > 0
        for group in program_data["groups"]:
            assert "header" in group
            assert "items" in group
            for item in group["items"]:
                assert "header" in item
                assert "sub_items" in item
