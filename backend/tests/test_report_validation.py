import os
import re
import sys

import pytest
from bs4 import BeautifulSoup

# Add backend/src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer


def create_robust_test_data():
    table_data = {
        "meet": [
            {
                "meet_name1": "Robust Test Meet",
                "meet_location": "Pool",
                "meet_start": "2024-01-01",
                "meet_end": "2024-01-01",
                "meet_class": 1,
                "meet_numlanes": 6,
            }
        ],
        "session": [
            {"sess_ptr": 1, "sess_no": 1, "sess_name": "Morning Session", "sess_day": 1, "sess_starttime": 32400}
        ],
        "sessitem": [
            {"sess_ptr": 1, "event_ptr": 1, "sess_rnd": "F", "sess_order": 1},
            {"sess_ptr": 1, "event_ptr": 2, "sess_rnd": "F", "sess_order": 2},
            {"sess_ptr": 1, "event_ptr": 3, "sess_rnd": "F", "sess_order": 3},
            {"sess_ptr": 1, "event_ptr": 99, "sess_rnd": "F", "sess_order": 4},
        ],
        "event": [
            {
                "event_ptr": 1,
                "event_no": 1,
                "ind_rel": "I",
                "event_gender": "F",
                "event_dist": 25,
                "event_stroke": "A",
                "low_age": 0,
                "high_age": 6,
                "event_sex": "Girls",
            },
            {
                "event_ptr": 2,
                "event_no": 2,
                "ind_rel": "I",
                "event_gender": "M",
                "event_dist": 25,
                "event_stroke": "A",
                "low_age": 7,
                "high_age": 8,
                "event_sex": "Boys",
            },
            {
                "event_ptr": 3,
                "event_no": 3,
                "ind_rel": "I",
                "event_gender": "X",
                "event_dist": 50,
                "event_stroke": "A",
                "low_age": 9,
                "high_age": 10,
                "event_sex": "Mixed",
            },
            {
                "event_ptr": 99,
                "event_no": 99,
                "ind_rel": "R",
                "event_gender": "X",
                "event_dist": 100,
                "event_stroke": "E",
                "low_age": 15,
                "high_age": 18,
                "event_sex": "Mixed",
            },
        ],
        "team": [
            {"team_no": 1, "team_abbr": "TST", "team_name": "TeamA", "team_short": "TeamA", "team_lsc": "PC"},
            {"team_no": 2, "team_abbr": "OTH", "team_name": "TeamB", "team_short": "TeamB", "team_lsc": "PC"},
        ],
        "athlete": [
            {
                "ath_no": 1,
                "team_no": 1,
                "last_name": "Girls",
                "first_name": "Six",
                "sex": "F",
                "ath_age": 5,
                "team": "TeamA",
            },
            {
                "ath_no": 2,
                "team_no": 1,
                "last_name": "Boys",
                "first_name": "Eight",
                "sex": "M",
                "ath_age": 8,
                "team": "TeamA",
            },
            {
                "ath_no": 3,
                "team_no": 2,
                "last_name": "Mixed",
                "first_name": "Ten",
                "sex": "F",
                "ath_age": 10,
                "team": "TeamB",
            },
        ],
        "entry": [
            {
                "event_ptr": 1,
                "ath_no": 1,
                "fin_heat": 1,
                "fin_lane": 1,
                "convseed_time": 20.0,
                "round1": "F",
                "team": "TeamA",
            },
            {
                "event_ptr": 2,
                "ath_no": 2,
                "fin_heat": 1,
                "fin_lane": 1,
                "convseed_time": 22.0,
                "round1": "F",
                "team": "TeamA",
            },
            {
                "event_ptr": 3,
                "ath_no": 3,
                "fin_heat": 1,
                "fin_lane": 1,
                "convseed_time": 45.0,
                "round1": "F",
                "team": "TeamB",
            },
        ],
        "relay": [
            {
                "event_ptr": 99,
                "team_no": 1,
                "team_ltr": "A",
                "convseed_time": 60.0,
                "fin_heat": 1,
                "fin_lane": 1,
                "round1": "F",
                "team": "TeamA",
            }
        ],
        "relaynames": [{"event_ptr": 99, "team_no": 1, "team_ltr": "A", "ath_no": 1, "pos": 1, "event_round": "F"}],
    }
    return table_data


def test_a_parents_lineup_logic():
    """a) 'Line-Up Parents Programs' for specific team, age, gender."""
    table_data = create_robust_test_data()
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    renderer = WeasyRenderer("dummy.pdf")

    # Test TeamA, Girls, 6 & under
    data = extractor.extract_meet_program_data(team_filter="TeamA", gender_filter="Girls", age_group_filter="6 & under")
    html = renderer.render_to_html(data)
    soup = BeautifulSoup(html, "html.parser")

    headers = [h.text.strip() for h in soup.find_all("div", class_="event-header")]
    assert any("Event 1" in h for h in headers)

    # Test Mixed inclusion: TeamB, Girls, 9-10
    data_mixed = extractor.extract_meet_program_data(
        team_filter="TeamB", gender_filter="Girls", age_group_filter="9-10"
    )
    html_mixed = renderer.render_to_html(data_mixed)
    soup_mixed = BeautifulSoup(html_mixed, "html.parser")
    headers_mixed = [h.text.strip() for h in soup_mixed.find_all("div", class_="event-header")]
    assert any("Event 3" in h and "Mixed" in h for h in headers_mixed)


def test_b_coaches_program_logic():
    """b) 'Coaches Meet Program' - all teams/events, 2-column, relays."""
    table_data = create_robust_test_data()
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    renderer = WeasyRenderer("dummy.pdf")

    data = extractor.extract_meet_program_data(columns_on_page=2, show_relay_swimmers=True)
    html = renderer.render_to_html(data)
    soup = BeautifulSoup(html, "html.parser")

    headers = [h.text.strip() for h in soup.find_all("div", class_="event-header")]
    assert len(headers) >= 4
    # Check for Relay in title
    relay_header = next(h for h in headers if "Event 99" in h)
    assert "Relay" in relay_header

    # Check Timestamp format: HH:MM AM/PM YYYY/MM/DD
    timestamp_span = soup.find("span", class_="right")
    assert timestamp_span is not None
    assert re.search(r"\d{2}:\d{2} (AM|PM) \d{4}/\d{2}/\d{2}", timestamp_span.text)

    style_tag = soup.find("style")
    assert "column-count: 2" in style_tag.text
    assert len(soup.find_all("div", class_="relay-swimmer")) > 0


def test_c_posting_program_logic():
    """c) 'Line Up Program for Posting' - gender separate, entry times, 2-column."""
    table_data = create_robust_test_data()
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    renderer = WeasyRenderer("dummy.pdf")

    data = extractor.extract_meet_program_data(gender_filter="Girls", columns_on_page=2)
    html = renderer.render_to_html(data)
    soup = BeautifulSoup(html, "html.parser")

    headers = [h.text.strip() for h in soup.find_all("div", class_="event-header")]
    assert any("Event 1" in h for h in headers)
    assert not any("Event 2" in h for h in headers)
    assert any("Event 3" in h for h in headers)

    time_cells = soup.find_all("td", class_="col-seed")
    assert len(time_cells) > 0
    assert any("20.000" in t.text for t in time_cells)


def test_d_computer_team_program_logic():
    """d) 'Computer Team Meet Program' - all teams/events, 1-column."""
    table_data = create_robust_test_data()
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    renderer = WeasyRenderer("dummy.pdf")

    data = extractor.extract_meet_program_data(columns_on_page=1)
    html = renderer.render_to_html(data)
    soup = BeautifulSoup(html, "html.parser")

    style_tag = soup.find("style")
    assert "column-count: 1" in style_tag.text

    headers = [h.text.strip() for h in soup.find_all("div", class_="event-header")]
    assert len(headers) >= 4


if __name__ == "__main__":
    pytest.main([__file__])
