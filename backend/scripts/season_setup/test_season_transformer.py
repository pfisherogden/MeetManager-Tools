
import pytest
from season_transformer import SeasonTransformer


@pytest.fixture
def sample_data():
    return {
        "MEET": [{"meet_name1": "Old Meet", "meet_start": "2025-06-01", "meet_numlanes": 6}],
        "TEAM": [
            {"TCode": "DP", "TName": "Del Prado Stingrays"},
            {"TCode": "FAST", "TName": "FAST Dolphins"},
            {"TCode": "OLD", "TName": "Old Team"}
        ],
        "ATHLETE": [{"Athlete": 1, "First": "John", "Last": "Doe"}],
        "ENTRY": [{"Entry": 1, "Athlete": 1, "MtEvent": 1}],
        "RELAY": [{"RELAY": 1, "TEAM": 1}],
        "SESSIONS": [{"Sess_no": 1, "Sess_name": "AM", "Sess_ptr": 1}, {"Sess_no": 2, "Sess_name": "PM", "Sess_ptr": 2}],
        "MTEVENT": [
            {"MtEvent": 1, "MtEv": 1, "Session": 1, "Event_sex": "G", "Event_stroke": "E", "Ind_rel": "R", "Low_age": 0, "High_Age": 6, "Num_prelanes": 6, "Std_lanes": " "},
            {"MtEvent": 2, "MtEv": 2, "Session": 2, "Event_sex": "B", "Event_stroke": "A", "Ind_rel": "I", "Low_age": 7, "High_Age": 8, "Num_prelanes": 6, "Std_lanes": " "}
        ],
        "Scoring": [{"score_place": i, "ind_score": 0.0, "rel_score": 0.0} for i in range(1, 17)],
        "StdLanes": [],
        "Sessitem": []
    }

def test_purge_data(sample_data):
    transformer = SeasonTransformer(sample_data)
    transformer.purge_data(preserve_team_abbr="DP")

    assert len(transformer.table_data["ATHLETE"]) == 0
    assert len(transformer.table_data["ENTRY"]) == 0
    assert len(transformer.table_data["RELAY"]) == 0

    team_codes = [t.get("TCode") or t.get("tcode") for t in transformer.table_data["TEAM"]]
    assert "DP" in team_codes
    assert "OLD" not in team_codes

def test_update_meet(sample_data):
    transformer = SeasonTransformer(sample_data)
    transformer.update_meet("New Season", "2026-06-01", 8, age_up="2026-06-01")

    meet = transformer.table_data["MEET"][0]
    # Check mappings (SeasonTransformer uses logical names but preserves casing)
    assert meet["meet_name1"] == "New Season"
    assert meet["meet_numlanes"] == 8

    # Check that events were also updated
    for event in transformer.table_data["MTEVENT"]:
        assert event["Num_prelanes"] == 8
        assert event["Std_lanes"] == "A"

def test_championship_scoring(sample_data):
    """Ensures Champs scoring uses 12 individual places and 8 relay places."""
    transformer = SeasonTransformer(sample_data)
    transformer.setup_scoring_and_seeding(is_champs=True)

    scoring = transformer.table_data["Scoring"]

    # Individual: 1st=20, 12th=5, 13th=0
    assert float(scoring[0]["ind_score"]) == 20.0
    assert float(scoring[11]["ind_score"]) == 5.0
    assert float(scoring[12]["ind_score"]) == 0.0

    # Relays: 1st=40, 5th=28, 8th=22, 9th=0
    assert float(scoring[0]["rel_score"]) == 40.0
    assert float(scoring[4]["rel_score"]) == 28.0
    assert float(scoring[7]["rel_score"]) == 22.0
    assert float(scoring[8]["rel_score"]) == 0.0

def test_dual_scoring(sample_data):
    """Ensures Dual scoring uses 4 individual places and 2 relay places."""
    transformer = SeasonTransformer(sample_data)
    transformer.setup_scoring_and_seeding(is_champs=False)

    scoring = transformer.table_data["Scoring"]

    # Individual: 1st=5, 4th=1
    assert float(scoring[0]["ind_score"]) == 5.0
    assert float(scoring[3]["ind_score"]) == 1.0
    assert float(scoring[4]["ind_score"]) == 0.0

    # Relays: 1st=10, 2nd=6, 3rd=0
    assert float(scoring[0]["rel_score"]) == 10.0
    assert float(scoring[1]["rel_score"]) == 6.0
    assert float(scoring[2]["rel_score"]) == 0.0

def test_consolidate_sessions_dual(sample_data):
    transformer = SeasonTransformer(sample_data)
    transformer.consolidate_sessions(is_champs=False)

    assert len(transformer.table_data["SESSIONS"]) == 1
    assert transformer.table_data["SESSIONS"][0]["Sess_no"] == 1

    # Check event linking
    for event in transformer.table_data["MTEVENT"]:
        assert event["Session"] == 1

def test_consolidate_sessions_champs(sample_data):
    """Ensures Champs layout creates 7 sessions and links events correctly."""
    transformer = SeasonTransformer(sample_data)
    transformer.consolidate_sessions(is_champs=True)

    assert len(transformer.table_data["SESSIONS"]) == 7

    events = transformer.table_data["MTEVENT"]
    # Event 1: Sex G, Stroke E, Ind_rel R -> Med Relays (Session 1)
    assert events[0]["Session"] == 1
    # Event 2: Sex B, Stroke A, Ind_rel I -> Freestyle (Session 2)
    assert events[1]["Session"] == 2

    # Check Sessitem
    sessitems = transformer.table_data["Sessitem"]
    assert len(sessitems) == 2
    assert sessitems[0]["Sess_ptr"] == 1
    assert sessitems[1]["Sess_ptr"] == 2

def test_ensure_std_lanes(sample_data):
    """Ensures standard seeding orders are created with correct MM column names."""
    transformer = SeasonTransformer(sample_data)
    transformer.ensure_std_lanes()

    std_lanes = transformer.table_data["StdLanes"]
    assert len(std_lanes) == 12

    # Check 6 lanes order: 3, 4, 2, 5, 1, 6
    row6 = next(r for r in std_lanes if r["Lanes"] == 6)
    assert row6["Order1"] == 3
    assert row6["Order6"] == 6

def test_ensure_team_exists(sample_data):
    transformer = SeasonTransformer(sample_data)
    transformer.ensure_team_exists("CW", "Castlewood")

    team_codes = [t.get("TCode") or t.get("tcode") for t in transformer.table_data["TEAM"]]
    assert "CW" in team_codes

def test_inject_memorized_reports(sample_data):
    """Ensures standard report presets are added."""
    transformer = SeasonTransformer(sample_data)
    transformer.inject_memorized_reports(team_abbr="DP")

    reports = transformer.table_data["MemorizedReports"]
    report_names = [r["Mem_Name"] for r in reports]

    assert "Lineup: 6&U" in report_names
    assert "Results: Coach" in report_names
    assert "Posting: Girls only" in report_names
    assert "Posting: Boys+Mixed" in report_names

    # Check DP filter
    lineup_6u = next(r for r in reports if r["Mem_Name"] == "Lineup: 6&U")
    assert lineup_6u["Team_Abbr"] == "DP"
    assert lineup_6u["Sess_Row"] == 4

def test_create_report_sessions(sample_data):
    """Ensures report-specific sessions are created and events are linked."""
    transformer = SeasonTransformer(sample_data)
    transformer.create_report_sessions()

    sessions = transformer.table_data["SESSIONS"]
    sess_names = [s.get("Sess_name") or s.get("SessName") for s in sessions]

    assert "Girls (F)" in sess_names
    assert "Lineup: 6&U" in sess_names

    # Check linkage
    girls_sess = next(s for s in sessions if s["Sess_name"] == "Girls (F)")
    sess_ptr = girls_sess["Sess_ptr"]

    items = [i for i in transformer.table_data["Sessitem"] if i["Sess_ptr"] == sess_ptr]
    assert len(items) == 1  # Event 1 is G
