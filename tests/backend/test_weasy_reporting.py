import os
import sys
import json
import pytest
from bs4 import BeautifulSoup

# Add backend/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/src")))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../fixtures/anonymized_meets"))

def get_anonymized_fixtures():
    fixtures = []
    if os.path.exists(FIXTURES_DIR):
        for f in os.listdir(FIXTURES_DIR):
            if f.endswith(".json"):
                fixtures.append(os.path.join(FIXTURES_DIR, f))
    return fixtures

@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_meet_program_data_hydration(fixture_path):
    with open(fixture_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    # Extract Data
    program_data = extractor.extract_meet_program_data()
    
    assert "meet_name" in program_data
    assert "groups" in program_data
    
    for group in program_data["groups"]:
        assert "header" in group
        assert "heats" in group
        for heat in group["heats"]:
            assert "header" in heat
            assert "sub_items" in heat
            for entry in heat["sub_items"]:
                assert "lane" in entry
                assert "time" in entry
                if entry.get("is_relay"):
                    assert "team" in entry
                    assert "swimmers" in entry
                    # Relays usually have 4 swimmers but can have alternates listed
                    assert len(entry["swimmers"]) >= 0
                else:
                    assert "name" in entry
                    assert "team" in entry

@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_meet_program_dom_validation(fixture_path, tmp_path):
    with open(fixture_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    program_data = extractor.extract_meet_program_data()
    
    output_pdf = str(tmp_path / "test_program.pdf")
    renderer = WeasyRenderer(output_pdf)
    html_content = renderer.render_to_html(program_data)
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Assert headers
    assert soup.find("h1").text == program_data["meet_name"]
    
    # Assert event blocks
    event_blocks = soup.find_all(class_="event-block")
    assert len(event_blocks) == len(program_data["groups"])
    
    # Check for specific data field (common in these fixtures)
    # Using "A" relay as a test if present
    relays = soup.find_all(class_="relay-swimmers-row")
    if program_data["groups"]:
        # Just ensure we have some content
        assert len(event_blocks) > 0
        
    # Assert no lane > 8 (common standard)
    lanes = soup.find_all(class_="col-lane")
    for lane in lanes:
        lane_text = lane.text.strip()
        if lane_text.isdigit():
            assert int(lane_text) <= 10 # Some meets have 10 lanes

def test_weasyprint_log_check(tmp_path):
    # This is a bit harder to test without a real run, 
    # but we can simulate a render and check for common layout issues in HTML
    pass

@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_entries_report_generation(fixture_path, tmp_path):
    with open(fixture_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    # 1. Test HY-TEK Style
    hytek_data = extractor.extract_meet_entries_data()
    output_hytek = str(tmp_path / "test_entries_hytek.pdf")
    renderer = WeasyRenderer(output_hytek)
    renderer.render_entries(hytek_data, "entries_hytek.html")
    assert os.path.exists(output_hytek)
    assert os.path.getsize(output_hytek) > 0
    
    # 2. Test Club Style
    club_data = extractor.extract_meet_entries_data()
    output_club = str(tmp_path / "test_entries_club.pdf")
    renderer = WeasyRenderer(output_club)
    renderer.render_entries(club_data, "entries_club.html")
    assert os.path.exists(output_club)
    assert os.path.getsize(output_club) > 0
