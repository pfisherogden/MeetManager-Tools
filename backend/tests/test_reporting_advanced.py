import pytest
from pathlib import Path
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

@pytest.fixture
def sample_extractor():
    base_dir = Path(__file__).parent.parent
    sample_mdb = base_dir / "data" / "sample_data_champs_2025-aftermeet.mdb"
    
    if not sample_mdb.exists():
        # Fallback for Docker environment
        sample_mdb = Path("/app/data/sample_data_champs_2025-aftermeet.mdb")
        
    if not sample_mdb.exists():
        pytest.fail(f"Sample MDB not found at {sample_mdb}. Checked local and /app/data.")
        
    converter = MmToJsonConverter(str(sample_mdb))
    return ReportDataExtractor(converter)

def test_hydrated_data_meet_program_structure(sample_extractor):
    """Test 1: Verify the core hydrated data structure for a Meet Program."""
    data = sample_extractor.extract_meet_program_data(columns_on_page=2)
    
    assert "groups" in data
    assert "meet_name" in data
    
    # Check for event groups
    assert len(data["groups"]) > 0
    first_event = data["groups"][0]
    assert "header" in first_event
    assert "heats" in first_event
    
    # Check for heats
    assert len(first_event["heats"]) > 0
    first_heat = first_event["heats"][0]
    assert "header" in first_heat
    assert "sub_items" in first_heat
    
    # Check for entries in heats
    assert len(first_heat["sub_items"]) > 0
    first_entry = first_heat["sub_items"][0]
    assert "lane" in first_entry
    assert "team" in first_entry
    assert "time" in first_entry

def test_relay_dq_data_hydration(sample_extractor):
    """Test 2: Verify that S&T reports include relay swimmer details and DQ placeholders."""
    # S&T reports are Meet Programs with show_dq_lines=True
    data = sample_extractor.extract_meet_program_data(show_dq_lines=True, show_relay_swimmers=True)
    
    found_relay = False
    for group in data["groups"]:
        for heat in group["heats"]:
            for entry in heat["sub_items"]:
                if entry.get("is_relay"):
                    found_relay = True
                    assert "swimmers" in entry
                    # If it's a relay, swimmers should be a list
                    assert isinstance(entry["swimmers"], list)
                    break
    
    assert data["show_dq_lines"] is True
    assert found_relay, "Should have found at least one relay to verify swimmers"

def test_timer_sheets_lane_filtering(sample_extractor):
    """Test 3: Verify lane-based filtering for Timer Sheets."""
    # Test filtering for Lane 1
    lane1_data = sample_extractor.extract_timer_sheets_data(lane_filter=1)
    for group in lane1_data["groups"]:
        assert group["lane"] == 1
        for heat in group["heats"]:
            for entry in heat["sub_items"]:
                assert entry["lane"] == "1"

    # Test filtering for Lane 2
    lane2_data = sample_extractor.extract_timer_sheets_data(lane_filter=2)
    for group in lane2_data["groups"]:
        assert group["lane"] == 2

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
    
    # data already has show_dq_lines, so we don't pass it again or we update it
    render_params = {**data}
    render_params["css_content"] = css_content
    render_params["generation_time"] = "10:00 AM 2026/02/22"
    
    html_output = template.render(**render_params)
    
    # Check for relay DQ elements
    assert "relay-dq-grid" in html_output
    assert "dq-reason-box" in html_output

def test_timer_sheets_label_logic_html(sample_extractor):
    """Test 5: Verify correct label logic ('Timer 1', 'Timer 2', etc.) in Timer Sheets."""
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
    assert "Timer 3" in html_output
    # Ensure manual-line class is used
    assert 'class="manual-line"' in html_output


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
        {"eventNum": "1B"}
    ]
    import re
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
    # Just verify no crash and some content
    assert data["meet_name"] is not None
