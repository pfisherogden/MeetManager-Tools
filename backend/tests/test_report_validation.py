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
                "Meet_name1": "Robust Test Meet",
                "Meet_location": "Pool",
                "Meet_start": "2024-01-01",
                "Meet_end": "2024-01-01",
                "Meet_class": 1,
                "Meet_numlanes": 6,
            }
        ],
        "session": [
            {"Sess_ptr": 1, "Sess_no": 1, "Sess_name": "Morning Session", "Sess_day": 1, "Sess_starttime": 32400}
        ],
        "sessitem": [
            {"Sess_ptr": 1, "Event_ptr": 1, "Sess_rnd": "F", "Sess_order": 1},
            {"Sess_ptr": 1, "Event_ptr": 2, "Sess_rnd": "F", "Sess_order": 2},
            {"Sess_ptr": 1, "Event_ptr": 3, "Sess_rnd": "F", "Sess_order": 3},
            {"Sess_ptr": 1, "Event_ptr": 99, "Sess_rnd": "F", "Sess_order": 4},
        ],
        "event": [
            {
                "Event_ptr": 1,
                "Event_no": 1,
                "Ind_rel": "I",
                "Event_gender": "F",
                "Event_dist": 25,
                "Event_stroke": "A",
                "Low_age": 0,
                "High_age": 6,
                "Event_sex": "Girls",
            },
            {
                "Event_ptr": 2,
                "Event_no": 2,
                "Ind_rel": "I",
                "Event_gender": "M",
                "Event_dist": 25,
                "Event_stroke": "A",
                "Low_age": 7,
                "High_age": 8,
                "Event_sex": "Boys",
            },
            {
                "Event_ptr": 3,
                "Event_no": 3,
                "Ind_rel": "I",
                "Event_gender": "X",
                "Event_dist": 50,
                "Event_stroke": "A",
                "Low_age": 9,
                "High_age": 10,
                "Event_sex": "Mixed",
            },
            {
                "Event_ptr": 99,
                "Event_no": 99,
                "Ind_rel": "R",
                "Event_gender": "X",
                "Event_dist": 100,
                "Event_stroke": "E",
                "Low_age": 15,
                "High_age": 18,
                "Event_sex": "Mixed",
            },
        ],
        "team": [
            {"Team_no": 1, "Team_abbr": "TST", "Team_name": "TeamA", "Team_short": "TeamA", "Team_lsc": "PC"},
            {"Team_no": 2, "Team_abbr": "OTH", "Team_name": "TeamB", "Team_short": "TeamB", "Team_lsc": "PC"},
        ],
        "athlete": [
            {
                "Ath_no": 1,
                "Team_no": 1,
                "Last_name": "Girls",
                "First_name": "Six",
                "Sex": "F",
                "Ath_age": 5,
                "team": "TeamA",
            },
            {
                "Ath_no": 2,
                "Team_no": 1,
                "Last_name": "Boys",
                "First_name": "Eight",
                "Sex": "M",
                "Ath_age": 8,
                "team": "TeamA",
            },
            {
                "Ath_no": 3,
                "Team_no": 2,
                "Last_name": "Mixed",
                "First_name": "Ten",
                "Sex": "F",
                "Ath_age": 10,
                "team": "TeamB",
            },
        ],
        "entry": [
            {
                "Event_ptr": 1,
                "Ath_no": 1,
                "Fin_heat": 1,
                "Fin_lane": 1,
                "ConvSeed_time": 20.0,
                "Round1": "F",
                "team": "TeamA",
            },
            {
                "Event_ptr": 2,
                "Ath_no": 2,
                "Fin_heat": 1,
                "Fin_lane": 1,
                "ConvSeed_time": 22.0,
                "Round1": "F",
                "team": "TeamA",
            },
            {
                "Event_ptr": 3,
                "Ath_no": 3,
                "Fin_heat": 1,
                "Fin_lane": 1,
                "ConvSeed_time": 45.0,
                "Round1": "F",
                "team": "TeamB",
            },
        ],
        "relay": [
            {
                "Event_ptr": 99,
                "Team_no": 1,
                "Team_ltr": "A",
                "ConvSeed_time": 60.0,
                "Fin_heat": 1,
                "Fin_lane": 1,
                "Round1": "F",
                "team": "TeamA",
            }
        ],
        "relaynames": [{"Event_ptr": 99, "Team_no": 1, "Team_ltr": "A", "Ath_no": 1, "Pos": 1, "Event_round": "F"}],
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
    assert len(soup.find_all("td", class_="swimmers-list")) > 0


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

    time_cells = soup.find_all("td", class_="col-time")
    assert len(time_cells) > 0
    assert any("20.00" in t.text for t in time_cells)


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
