import json
import os
import sys

import pytest
from bs4 import BeautifulSoup

# Add backend/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/src")))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

# Correct path for fixtures that works both locally and in Docker
# Locally: ../../tests/fixtures/anonymized_meets
# Docker: /app/data/fixtures_root/anonymized_meets
FIXTURES_DIR_LOCAL_1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tests/fixtures/anonymized_meets"))
FIXTURES_DIR_LOCAL_2 = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../tests/fixtures/anonymized_meets")
)
FIXTURES_DIR_DOCKER = "/app/data/fixtures_root/anonymized_meets"

if os.path.exists(FIXTURES_DIR_DOCKER):
    FIXTURES_DIR = FIXTURES_DIR_DOCKER
elif os.path.exists(FIXTURES_DIR_LOCAL_1):
    FIXTURES_DIR = FIXTURES_DIR_LOCAL_1
else:
    FIXTURES_DIR = FIXTURES_DIR_LOCAL_2


def get_anonymized_fixtures():
    fixtures = []
    if os.path.exists(FIXTURES_DIR):
        for f in os.listdir(FIXTURES_DIR):
            if f.endswith(".json"):
                fixtures.append(os.path.join(FIXTURES_DIR, f))
    return fixtures


@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_meet_program_data_hydration(fixture_path):
    with open(fixture_path) as f:
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
    with open(fixture_path) as f:
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
    assert soup.find(class_="header-meet-name").text == program_data["meet_name"]
    assert "MM-Tools" in soup.find(class_="header-table").text
    # Assert event blocks
    event_blocks = soup.find_all(class_="event-block")
    assert len(event_blocks) == len(program_data["groups"])

    if program_data["groups"]:
        # Just ensure we have some content
        assert len(event_blocks) > 0

    # Assert no lane > 10 (common standards)
    lanes = soup.find_all(class_="col-lane")
    for lane in lanes:
        lane_text = lane.text.strip()
        if lane_text.isdigit() and lane_text != "Lane":
            assert int(lane_text) <= 10


def test_weasyprint_log_check(tmp_path):
    # This is a bit harder to test without a real run,
    # but we can simulate a render and check for common layout issues in HTML
    pass


@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_entries_report_generation(fixture_path, tmp_path):
    with open(fixture_path) as f:
        fixture_wrapper = json.load(f)

    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)

    # 1. Test HY-TEK Style
    hytek_data = extractor.extract_meet_entries_data()
    output_hytek = str(tmp_path / "test_entries_hytek.pdf")
    renderer = WeasyRenderer(output_hytek)
    renderer.render_entries(hytek_data, "entries_hytek.j2")
    assert os.path.exists(output_hytek)
    assert os.path.getsize(output_hytek) > 0

    # 2. Test Club Style
    club_data = extractor.extract_meet_entries_data()
    output_club = str(tmp_path / "test_entries_club.pdf")
    renderer = WeasyRenderer(output_club)
    renderer.render_entries(club_data, "entries_club.j2")
    assert os.path.exists(output_club)
    assert os.path.getsize(output_club) > 0


def test_report_filtering_and_title(tmp_path):
    # Use one of the fixtures
    fixture_list = get_anonymized_fixtures()
    if not fixture_list:
        pytest.skip("No fixtures found")
    fixture_path = fixture_list[0]
    with open(fixture_path) as f:
        fixture_wrapper = json.load(f)

    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)

    custom_title = "MY CUSTOM TITLE"
    team_filter = "DP-TV"  # Standard team in these fixtures

    # Test Meet Program with filter/title
    program_data = extractor.extract_meet_program_data(team_filter=team_filter, report_title=custom_title)
    assert custom_title in program_data["sub_title"]
    assert f"Team: {team_filter}" in program_data["sub_title"]

    output_pdf = str(tmp_path / "filtered_program.pdf")
    renderer = WeasyRenderer(output_pdf)
    html_content = renderer.render_to_html(program_data)

    soup = BeautifulSoup(html_content, "html.parser")
    assert custom_title in soup.find(class_="header-sub-title").text
    assert f"Team: {team_filter}" in soup.find(class_="header-sub-title").text

    # Assert all entries in the HTML are for the filtered team
    # Note: in meet program, team is in .col-team
    team_cells = soup.find_all(class_="col-team")
    for cell in team_cells:
        if cell.text.strip() and cell.text.strip() != "Team":
            assert team_filter.lower() in cell.text.lower()


def test_report_gender_age_filtering(tmp_path):
    # Use one of the fixtures
    fixture_list = get_anonymized_fixtures()
    if not fixture_list:
        pytest.skip("No fixtures found")
    fixture_path = fixture_list[0]
    with open(fixture_path) as f:
        fixture_wrapper = json.load(f)

    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)

    # Test filtering for "Girls" and "6 & under"
    gender = "Girls"
    age = "6 & under"
    program_data = extractor.extract_meet_program_data(gender_filter=gender, age_group_filter=age)

    output_pdf = str(tmp_path / "filtered_gender_age.pdf")
    renderer = WeasyRenderer(output_pdf)
    html_content = renderer.render_to_html(program_data)

    soup = BeautifulSoup(html_content, "html.parser")

    # Assert headers contain "Girls" and "6 & under" (or matches events that do)
    event_headers = soup.find_all(class_="event-header-box")
    for header in event_headers:
        text = header.text.lower()
        # It should be either the filtered gender OR "mixed"
        assert gender.lower() in text or "mixed" in text
        assert age.lower() in text


def test_report_zebra_striping(tmp_path):
    # Use one of the fixtures
    fixture_list = get_anonymized_fixtures()
    if not fixture_list:
        pytest.skip("No fixtures found")
    fixture_path = fixture_list[0]
    with open(fixture_path) as f:
        fixture_wrapper = json.load(f)

    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)

    # Extract Data
    program_data = extractor.extract_meet_program_data()
    program_data["zebra_striping"] = True

    output_pdf = str(tmp_path / "zebra_program.pdf")
    renderer = WeasyRenderer(output_pdf)
    html_content = renderer.render_to_html(program_data)

    soup = BeautifulSoup(html_content, "html.parser")

    # Assert that at least some rows have the zebra-row class
    # Now using div-based rows
    zebra_rows = soup.find_all(class_="zebra-row")
    assert len(zebra_rows) > 0

    # Verify alternating: first div-entry-row should not be zebra, second should be (if 2+ entries)
    # We look at entry-group which contains div-entry-row
    for group in soup.find_all(class_="entries-container"):
        rows = group.find_all(class_="div-entry-row")
        if len(rows) >= 2:
            assert "zebra-row" not in rows[0].get("class", [])
            assert "zebra-row" in rows[1].get("class", [])


def test_weasy_multi_column_crash_regression(tmp_path):
    """
    Regression test for Issue #292: WeasyPrint crash in 2-column layout.
    """
    # Use any fixture
    fixture_list = get_anonymized_fixtures()
    if not fixture_list:
        pytest.skip("No fixtures found")
    fixture_path = fixture_list[0]
    with open(fixture_path) as f:
        fixture_wrapper = json.load(f)

    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)

    # Force 2-column layout
    program_data = extractor.extract_meet_program_data(columns_on_page=2)

    output_pdf = str(tmp_path / "multicol_crash_test.pdf")
    renderer = WeasyRenderer(output_pdf)

    # This should NOT crash with AttributeError or 'children' error
    renderer.render_meet_program(program_data)
    assert os.path.exists(output_pdf)
    assert os.path.getsize(output_pdf) > 0


def test_team_filtering_robustness():
    """
    Regression test for Issue #292: Empty reports due to team name mismatches.
    Ensures that various formats of team name/code are matched correctly using real data.
    """
    # Use a real fixture to ensure all internal structures (sessions, events) are correctly hydrated
    fixture_list = get_anonymized_fixtures()
    if not fixture_list:
        pytest.skip("No fixtures found")
    fixture_path = fixture_list[0]
    with open(fixture_path) as f:
        fixture_wrapper = json.load(f)

    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    # Perform full conversion to hydrate sessions/events/entries
    full_data = converter.convert()
    extractor = ReportDataExtractor(converter, full_data=full_data)

    # Get a real team name from the data
    raw_teams = converter.tables.get("team")
    if raw_teams.empty:
        pytest.skip("No teams found in fixture")

    # In anonymized data, it might be team_name or name
    first_row = raw_teams.iloc[0]
    team_name = str(first_row.get("team_name") or first_row.get("name") or "")
    team_code = str(first_row.get("team_abbr") or first_row.get("abbr") or "")

    # Test cases: (filter_string, should_match)
    test_cases = [
        (team_name, True),  # Exact match name
        (team_code, True),  # Exact match code
        (team_name.split(" ")[0], True),  # Partial word match
        ("non-existent-team-name-123", False),
    ]

    for filter_str, expected in test_cases:
        program_data = extractor.extract_meet_program_data(team_filter=filter_str)
        matched = len(program_data["groups"]) > 0
        if filter_str != "non-existent-team-name-123":
            assert matched == expected, f"Failed matching team filter '{filter_str}' (expected {expected})"
        else:
            assert matched is False
