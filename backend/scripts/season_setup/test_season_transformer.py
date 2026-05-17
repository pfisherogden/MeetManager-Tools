
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
        "SESSIONS": [{"SESSION": 1, "SessName": "AM"}, {"SESSION": 2, "SessName": "PM"}],
        "MTEVENT": [
            {"MtEvent": 1, "MtEv": 1, "Session": 1, "Event_stroke": "E", "Ind_rel": "R", "Num_prelanes": 6, "Std_lanes": " "},
            {"MtEvent": 2, "MtEv": 2, "Session": 2, "Event_stroke": "A", "Ind_rel": "I", "Num_prelanes": 6, "Std_lanes": " "}
        ],
        "Scoring": [{"score_place": i, "ind_score": 0.0, "rel_score": 0.0} for i in range(1, 17)],
        "StdLanes": []
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
    """Ensures Champs scoring uses 16 individual places and 8 relay places."""
    transformer = SeasonTransformer(sample_data)
    transformer.setup_scoring_and_seeding(is_champs=True)

    scoring = transformer.table_data["Scoring"]

    # Individual: 1st=20, 12th=5, 16th=1
    assert float(scoring[0]["ind_score"]) == 20.0
    assert float(scoring[11]["ind_score"]) == 5.0
    assert float(scoring[15]["ind_score"]) == 1.0

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
    # Event 1: Stroke E, Ind_rel R -> Med Relays (Session 1)
    assert events[0]["Session"] == 1
    # Event 2: Stroke A, Ind_rel I -> Freestyle (Session 2)
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
