import time

import pytest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


@pytest.fixture
def converter():
    # Use a small subset or mock data for fast tests
    data = {
        "meet": [{"meet_name1": "Test Meet", "meet_name": "Test Meet"}],
        "team": [{"team_no": 1, "team_name": "Team A", "team_abbr": "TA"}],
        "athlete": [{"ath_no": 1, "first_name": "John", "last_name": "Doe", "sex": "M", "team_no": 1}],
        "entry": [{"ath_no": 1, "event_ptr": 1, "seed_time": "1:23.45"}],
        "event": [
            {
                "event_no": 1,
                "event_num": 1,
                "event_desc": "50 Free",
                "is_relay": False,
                "gender": "M",
                "min_age": 0,
                "max_age": 109,
            }
        ],
    }
    return MmToJsonConverter(table_data=data)


def test_bug8_report_subtitle_naming(converter):
    extractor = ReportDataExtractor(converter)

    # Test with various filters
    res = extractor.extract_meet_program_data(
        team_filter="Team A", gender_filter="Boys", age_group_filter="9-10", report_title="Custom Title"
    )

    subtitle = res["sub_title"]
    assert "Custom Title" in subtitle
    assert "Team: Team A" in subtitle
    assert "Gender: Boys" in subtitle
    assert "Age: 9-10" in subtitle

    # Test default filters (should not show Gender: Mixed or Age: Open)
    res_default = extractor.extract_meet_program_data(report_title="Default Title")
    assert res_default["sub_title"] == "Default Title"


def test_bug6_report_extraction_performance(converter):
    extractor = ReportDataExtractor(converter)

    # Pre-warm cache
    extractor._get_full_data()

    start_time = time.time()
    # Simulate generating 10 reports (like a bundle)
    for _ in range(10):
        extractor.extract_meet_program_data()
        extractor.extract_meet_entries_data()

    duration = time.time() - start_time
    print(f"Extraction duration for 20 reports: {duration:.4f}s")

    # On small datasets this should be extremely fast (< 0.5s)
    # The fix was reusing the extractor/converter which we are doing here.
    assert duration < 1.0
