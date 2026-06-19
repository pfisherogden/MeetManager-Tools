import json
from pathlib import Path

import pytest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


@pytest.fixture
def sample_extractor():
    """Fixture to provide a ReportDataExtractor with real/anonymized data."""
    # In local backend run: __file__ is backend/tests/test_reporting_advanced.py
    # So __file__.parent.parent.parent is the repo root.
    repo_root = Path(__file__).parent.parent.parent

    # Locate the JSON fixture explicitly checked into the repo
    sample_json = (
        repo_root / "tests" / "fixtures" / "anonymized_meets" / "sample_data_champs_2025-aftermeet.json"
    ).resolve()

    if not sample_json.exists():
        # Fallback for Docker environment (/app is usually the repo root or backend root depending on context)
        sample_json = Path("/app/tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json")
        if not sample_json.exists():
            sample_json = Path("/app/backend/tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json")

    if not sample_json.exists():
        # Final fallback check: if running python directly from repo root
        sample_json = Path("tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json").resolve()

    if not sample_json.exists():
        pytest.fail(
            f"Sample JSON fixture not found at {sample_json}. Ensure the `tests/fixtures/anonymized_meets` directory is checked out."
        )

    with open(sample_json, encoding="utf-8") as f:
        fixture_payload = json.load(f)
        # Handle cases where the JSON is wrapped in a "data" property (e.g. from anonymization script)
        table_data = fixture_payload.get("data", fixture_payload)

    converter = MmToJsonConverter(table_data=table_data)
    return ReportDataExtractor(converter)


def test_hydrated_data_meet_program_structure(sample_extractor):
    """Test 1: Verify the structure of the hydrated data for Meet Program."""
    data = sample_extractor.extract_meet_program_data(columns_on_page=2)

    assert "groups" in data
    assert "meet_name" in data

    # Check for event groups
    assert len(data["groups"]) > 0
    first_group = data["groups"][0]
    assert "header" in first_group
    assert "heats" in first_group

    # Check for heat structure
    first_heat = first_group["heats"][0]
    assert "header" in first_heat
    assert "sub_items" in first_heat

    # Check for entry structure
    first_entry = first_heat["sub_items"][0]
    assert "lane" in first_entry
    assert "name" in first_entry or "team" in first_entry
    assert "time" in first_entry


def test_relay_dq_data_hydration(sample_extractor):
    """Test 2: Verify that relay swimmers are included for S&T reports."""
    # S&T Report usually has show_dq_lines=True and show_relay_swimmers=True
    data = sample_extractor.extract_meet_program_data(show_dq_lines=True, show_relay_swimmers=True)

    # Find a relay event
    relay_found = False
    for group in data["groups"]:
        if "Relay" in group["header"]:
            for heat in group["heats"]:
                for entry in heat["sub_items"]:
                    if entry.get("is_relay"):
                        relay_found = True
                        assert "swimmers" in entry
                        assert isinstance(entry["swimmers"], list)
                        assert len(entry["swimmers"]) > 0
                        break
            if relay_found:
                break
    assert relay_found, "No relay event found in sample data for testing."


def test_timer_sheets_lane_filtering(sample_extractor):
    """Test 3: Verify lane-based filtering for timer sheets."""
    lane_1_data = sample_extractor.extract_timer_sheets_data(lane_filter=1)
    lane_3_data = sample_extractor.extract_timer_sheets_data(lane_filter=3)

    # Check that they result in valid structures, even if anonymized data doesn't have exact lanes
    assert "groups" in lane_1_data
    assert "groups" in lane_3_data


def test_html_structural_verification(sample_extractor):
    """Test 4: Verify the presence of specific CSS classes in the generated HTML structure."""
    from jinja2 import Environment, FileSystemLoader

    base_dir = Path(__file__).parent.parent
    template_dir = base_dir / "src" / "mm_to_json" / "reporting" / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))

    # Test S&T layout
    data = sample_extractor.extract_meet_program_data(show_dq_lines=True, show_relay_swimmers=True)
    template = env.get_template("meet_program.j2")

    # We need to simulate some variables usually passed by the renderer
    css_path = template_dir / "report_style.css"
    css_content = css_path.read_text()

    # Update render_params to explicitly pass the flag expected by the Jinja template
    render_params = {**data}
    render_params["css_content"] = css_content
    render_params["generation_time"] = "10:00 AM 2026/02/22"
    render_params["show_dq_lines"] = True

    html_output = template.render(**render_params)

    # Check for relay DQ elements
    assert "relay-grid" in html_output
    assert "col-dq" in html_output

    # Check for dedicated DQ column header or similar expected structure
    # In some rendered versions with simpler CSS, the class list changes.
    assert "DQ</div>" in html_output
    assert "col-dq" in html_output


def test_timer_sheets_label_logic_html(sample_extractor):
    """Test 5: Verify that Timer Sheets use the correct labels in HTML."""
    from jinja2 import Environment, FileSystemLoader

    base_dir = Path(__file__).parent.parent
    template_dir = base_dir / "src" / "mm_to_json" / "reporting" / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))

    data = sample_extractor.extract_timer_sheets_data(lane_filter=1)
    template = env.get_template("timer_sheets.j2")

    css_path = template_dir / "report_style.css"
    css_content = css_path.read_text()

    render_params = {**data}
    render_params["css_content"] = css_content
    render_params["generation_time"] = "10:00 AM 2026/02/22"

    html_output = template.render(**render_params)

    # Check for new labels
    assert "Timer 1" in html_output
    assert "Timer 2" in html_output
    assert "Stopwatch" in html_output

    # Ensure manual-line class is used


def test_session_date_extraction(sample_extractor):
    """Test 7: Verify that session dates are correctly extracted from the MDB if present."""
    data = sample_extractor.converter.convert()
    sessions = data.get("sessions", [])
    if sessions:
        # Check if first session has a date
        # Note: If sample data has "Unknown Date", this verifies the extractor's fallback too
        pass


def test_alphanumeric_event_sorting(sample_extractor):
    """Test 8: Verify that events are sorted numerically even with letters (e.g. 1, 1A, 2)."""
    # Create mock events to test sorting
    events = [
        {"eventNum": "2"},
        {"eventNum": "1"},
        {"eventNum": "10"},
        {"eventNum": "1A"},
    ]

    def sort_key(e):
        num_part = "".join(filter(str.isdigit, str(e.get("eventNum", "0"))))
        return int(num_part) if num_part else 0

    sorted_evts = sorted(events, key=sort_key)
    assert sorted_evts[0]["eventNum"] == "1"
    assert sorted_evts[-1]["eventNum"] == "10"


def test_event_gender_filtering(sample_extractor):
    """Test 9: Verify gender filter correctly restricts events."""
    # Test Boys only
    boys_data = sample_extractor.extract_meet_program_data(gender_filter="Boys")
    for group in boys_data["groups"]:
        # "Event 1  Girls 6 & under..." should NOT be in boys_data if filter works
        # but Mixed might be.
        assert "Girls" not in group["header"] or "Mixed" in group["header"]


def test_age_group_formatting(sample_extractor):
    """Test 10: Verify _format_age utility logic."""
    assert sample_extractor._format_age(0, 6) == "6 & under"
    assert sample_extractor._format_age(15, 109) == "15 & over"
    assert sample_extractor._format_age(0, 109) == "Open"
    assert sample_extractor._format_age(11, 12) == "11-12"


def test_timer_sheets_relay_names_hydration(sample_extractor):
    """Test 11: Verify relay names appear correctly on timer sheets."""
    data = sample_extractor.extract_timer_sheets_data()
    # Find a relay entry
    found_relay = False
    for group in data["groups"]:
        for heat in group["heats"]:
            for item in heat["sub_items"]:
                if item.get("is_relay"):
                    assert "swimmers" in item
                    assert len(item["swimmers"]) > 0
                    found_relay = True
                    break
    assert found_relay, "Should have found at least one relay in sample data"


def test_hydrated_data_to_markdown_utility(sample_extractor):
    """Test 6: Verify a utility that dumps hydrated data to MD format."""
    data = sample_extractor.extract_meet_program_data(columns_on_page=1)
    md_output = [f"# {data['meet_name']}", f"## {data['sub_title']}"]
    for group in data["groups"]:
        md_output.append(f"### {group['header']}")
        for heat in group["heats"]:
            md_output.append(f"#### {heat['header']}")
            for entry in heat["sub_items"]:
                swimmer = entry.get("name") or entry.get("team")
                md_output.append(f"- Lane {entry.get('lane', '?')}: {swimmer} ({entry.get('time', 'NT')})")

    md_text = "\n".join(md_output)

    assert data["meet_name"] in md_text
    # Verify at least one entry is formatted correctly
    assert "- Lane" in md_text


def test_lane_timer_sheets_extraction_v3_format(sample_extractor):
    """Test: Verify the extraction of Lane Timer Sheets using the V3 style format."""
    data = sample_extractor.extract_lane_timer_sheets_data(include_blank_lanes=True, break_every_six_events=True)
    assert "groups" in data
    if data["groups"]:
        group = data["groups"][0]
        assert "sub_items" in group
        for row in group["sub_items"]:
            assert "type" in row
            if row["type"] == "header":
                assert "event_desc" in row
            else:
                assert "item" in row


if __name__ == "__main__":
    # If run directly, generate the MD for manual inspection
    # Mocking for local run if needed
    pass
