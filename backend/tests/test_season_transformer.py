import pytest
from mm_to_json.season_transformer import SeasonTransformer

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
            {"MtEvent": 1, "MtEv": 1, "Session": 1},
            {"MtEvent": 2, "MtEv": 2, "Session": 2}
        ]
    }

def test_purge_data(sample_data):
    transformer = SeasonTransformer(sample_data)
    # Mocking venues.json existence for the test isn't strictly necessary if we check against DP and standard teams
    transformer.purge_data(preserve_team_abbr="DP")
    
    assert len(sample_data["ATHLETE"]) == 0
    assert len(sample_data["ENTRY"]) == 0
    assert len(sample_data["RELAY"]) == 0
    
    # "OLD" should be removed, "DP" and "FAST" (if in venues.json) should stay.
    # Since venues.json is actually on disk in the real environment, we check what's there.
    # For this test, let's assume "FAST" is a standard team.
    team_codes = [t.get("TCode") for t in sample_data["TEAM"]]
    assert "DP" in team_codes
    assert "OLD" not in team_codes

def test_update_meet(sample_data):
    transformer = SeasonTransformer(sample_data)
    transformer.update_meet("New Season", "2026-06-01", 8, age_up="2026-06-01")
    
    meet = sample_data["MEET"][0]
    assert meet["meet_name1"] == "New Season"
    assert meet["meet_start"] == "2026-06-01"
    assert meet["meet_numlanes"] == 8
    assert meet["age_up"] == "2026-06-01"

def test_consolidate_sessions_dual(sample_data):
    transformer = SeasonTransformer(sample_data)
    transformer.consolidate_sessions(is_champs=False)
    
    assert len(sample_data["SESSIONS"]) == 1
    assert sample_data["SESSIONS"][0]["SESSION"] == 1
    
    for event in sample_data["MTEVENT"]:
        assert event["Session"] == 1

def test_consolidate_sessions_champs(sample_data):
    transformer = SeasonTransformer(sample_data)
    transformer.consolidate_sessions(is_champs=True)
    
    assert len(sample_data["SESSIONS"]) == 2
    assert sample_data["MTEVENT"][1]["Session"] == 2

def test_ensure_team_exists(sample_data):
    transformer = SeasonTransformer(sample_data)
    transformer.ensure_team_exists("CW", "Castlewood")
    
    team_codes = [t.get("TCode") for t in sample_data["TEAM"]]
    assert "CW" in team_codes
    
    # Should not add if already exists
    transformer.ensure_team_exists("DP", "Del Prado")
    assert len([t for t in sample_data["TEAM"] if t.get("TCode") == "DP"]) == 1
