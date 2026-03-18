import pytest
from bs4 import BeautifulSoup

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer


@pytest.fixture
def relay_data():
    return {
        "meet": [{"meet_name1": "Test Meet"}],
        "team": [{"team_no": 1, "team_name": "Del Prado Stingrays", "team_abbr": "DP", "team_short": "Del Prado"}],
        "athlete": [
            {
                "ath_no": 1,
                "first_name": "A",
                "last_name": "One",
                "sex": "Boys",
                "team_no": 1,
                "age": 10,
                "schoolyear": "",
            },
            {
                "ath_no": 2,
                "first_name": "B",
                "last_name": "Two",
                "sex": "Boys",
                "team_no": 1,
                "age": 10,
                "schoolyear": "",
            },
            {
                "ath_no": 3,
                "first_name": "C",
                "last_name": "Three",
                "sex": "Boys",
                "team_no": 1,
                "age": 10,
                "schoolyear": "",
            },
            {
                "ath_no": 4,
                "first_name": "D",
                "last_name": "Four",
                "sex": "Boys",
                "team_no": 1,
                "age": 10,
                "schoolyear": "",
            },
        ],
        "event": [
            {
                "event_no": 1,
                "event_ptr": 1,
                "ind_rel": "R",
                "sex": "Boys",
                "low_age": 9,
                "high_age": 10,
                "event_dist": 200,
                "event_stroke": "F",
                "event_rounds": 1,
                "num_prelanes": 6,
                "num_finlanes": 6,
            }
        ],
        "relay": [
            {
                "event_ptr": 1,
                "team_no": 1,
                "team_ltr": "A",
                "convseed_time": 150.0,  # 2:30.00
                "fin_heat": 1,
                "fin_lane": 3,
                "fin_time": 150.0,
                "fin_stat": "",
            }
        ],
        "relaynames": [
            {"event_ptr": 1, "team_no": 1, "team_ltr": "A", "event_round": "F", "ath_no": 1, "pos": 1},
            {"event_ptr": 1, "team_no": 1, "team_ltr": "A", "event_round": "F", "ath_no": 2, "pos": 2},
            {"event_ptr": 1, "team_no": 1, "team_ltr": "A", "event_round": "F", "ath_no": 3, "pos": 3},
            {"event_ptr": 1, "team_no": 1, "team_ltr": "A", "event_round": "F", "ath_no": 4, "pos": 4},
        ],
        "session": [{"sess_no": 1, "sess_name": "Saturday AM", "sess_ptr": 1, "sess_day": 1, "sess_starttime": 32400}],
        "sessitem": [{"sess_ptr": 1, "event_ptr": 1, "sess_rnd": "F", "sess_order": 1}],
        "entry": [],
        "divisions": [],
    }


def test_relay_swimmer_data_extraction(relay_data):
    converter = MmToJsonConverter(table_data=relay_data)
    extractor = ReportDataExtractor(converter)

    # Pre-check: Does convert() actually find entries?
    full = converter.convert()
    assert len(full["sessions"][0]["events"][0]["entries"]) > 0

    res = extractor.extract_meet_program_data()
    assert len(res["groups"]) > 0
    event = res["groups"][0]
    heat = event["heats"][0]
    entry = heat["sub_items"][0]

    assert entry["is_relay"] is True
    assert len(entry["swimmers"]) == 4
    assert any("One" in s for s in entry["swimmers"])
    assert any("Four" in s for s in entry["swimmers"])


def test_meet_program_formatting_rules(relay_data, tmp_path):
    converter = MmToJsonConverter(table_data=relay_data)
    extractor = ReportDataExtractor(converter)
    data = extractor.extract_meet_program_data(show_dq_lines=True)

    output_pdf = str(tmp_path / "issue_139_program.pdf")
    renderer = WeasyRenderer(output_pdf)
    html = renderer.render_to_html(data)

    soup = BeautifulSoup(html, "html.parser")
    # th.col-dq is expected if show_dq_lines is True
    assert soup.find("th", class_="col-dq") is not None

    # Check for 2x2 relay grid markers
    assert soup.find("div", class_="relay-grid") is not None


def test_timer_sheets_formatting(relay_data, tmp_path):
    converter = MmToJsonConverter(table_data=relay_data)
    extractor = ReportDataExtractor(converter)
    data = extractor.extract_timer_sheets_data()

    output_pdf = str(tmp_path / "issue_139_timer.pdf")
    renderer = WeasyRenderer(output_pdf)
    html = renderer.render_to_html(data, "timer_sheets.j2")

    soup = BeautifulSoup(html, "html.parser")
    # Verify we got groups and data
    assert "Del Prado Stingrays" in soup.get_text()
    assert soup.find(class_="entry-team-name") is not None
