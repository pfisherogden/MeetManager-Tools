import pytest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


@pytest.fixture
def sample_data():
    return {
        "meet": [{"meet_name1": "Test Meet"}],
        "team": [{"team_no": 1, "team_name": "Team A", "team_abbr": "TA"}],
        "athlete": [
            {"ath_no": 1, "first_name": "John", "last_name": "Doe", "sex": "M", "team_no": 1, "age": 10},
        ],
        "event": [
            {
                "event_no": 1,
                "event_ptr": 1,
                "ind_rel": "I",
                "sex": "M",
                "low_age": 9,
                "high_age": 10,
                "event_dist": 50,
                "event_stroke": "F",
                "event_rounds": 1,
            }
        ],
        "entry": [
            {
                "event_ptr": 1,
                "ath_no": 1,
                "fin_heat": 1,
                "fin_lane": 3,
                "convseed_time": 30.0,
            }
        ],
        "session": [{"sess_no": 1, "sess_name": "S1", "sess_ptr": 1}],
        "sessitem": [{"sess_ptr": 1, "event_ptr": 1, "sess_rnd": "F", "sess_order": 1}],
    }


def test_reproduce_mixed_gender_empty_report(sample_data):
    converter = MmToJsonConverter(table_data=sample_data)
    extractor = ReportDataExtractor(converter)

    # Test with Mixed gender filter (should NOT filter out anyone)
    res = extractor.extract_meet_program_data(gender_filter="Mixed")

    assert len(res["groups"]) > 0, "Groups should not be empty when gender_filter is 'Mixed'"
    event = res["groups"][0]
    assert len(event["heats"]) > 0
    heat = event["heats"][0]
    assert len(heat["sub_items"]) > 0, "Should have entries in the heat"

    # Verify legacy PDFRenderer builds elements from this data
    import tempfile

    from mm_to_json.reporting.config import ReportConfig
    from mm_to_json.reporting.renderer import PDFRenderer

    config = ReportConfig(title="Test")
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        renderer = PDFRenderer(tmp.name, config)
        elements = renderer._build_elements(res, 500)
        from reportlab.platypus import Table

        tables = [e for e in elements if isinstance(e, Table)]
        assert len(tables) > 0, "PDFRenderer failed to build tables; data likely missing from items key"
