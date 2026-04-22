import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))
# Add scripts to path for SeasonTransformer
sys.path.append(os.path.join(os.path.dirname(__file__), "../../scripts/season_setup"))

from season_transformer import SeasonTransformer

@pytest.fixture
def mock_template_data():
    return {
        "meet": [
            {
                "meet_name1": "Template Meet",
                "meet_start": "2020-01-01",
                "meet_end": "2020-01-01",
                "meet_numlanes": 6,
                "calc_date": "2020-06-01",
                "meet_location": "Template Pool"
            }
        ],
        "team": [
            {"TCode": "DP", "TName": "Del Prado Stingrays"},
            {"TCode": "FAST", "TName": "FAST Dolphins"}
        ],
        "athlete": [{"Athlete": 1, "First": "Old", "Last": "Swimmer"}],
        "entry": [{"Entry": 1, "Athlete": 1, "MtEvent": 1}],
        "relay": [{"RELAY": 1, "TEAM": 1}],
        "session": [{"SESSION": 1, "SessName": "Morning"}],
        "mtevent": [{"MtEvent": 1, "MtEv": 1, "Session": 1}],
        "scoring": [{"Ind1": 9, "Rel1": 12}]
    }

def test_season_transformer_hermetic(mock_template_data):
    """Verify that SeasonTransformer correctly modifies a mock dataset."""
    transformer = SeasonTransformer(mock_template_data)
    
    # 1. Purge data
    transformer.purge_data(preserve_team_abbr="DP")
    assert len(mock_template_data["athlete"]) == 0
    assert len(mock_template_data["entry"]) == 0
    assert len(mock_template_data["relay"]) == 0
    
    # 2. Update meet
    transformer.update_meet(
        name="2026 Test Meet",
        start_date="2026-05-30",
        lanes=8,
        location="FAST Pool",
        age_up="2026-06-01",
        entry_open="2025-06-01",
        entry_deadline="2026-05-26"
    )
    meet = mock_template_data["meet"][0]
    assert meet["meet_name1"] == "2026 Test Meet"
    assert meet["meet_numlanes"] == 8
    assert meet["calc_date"] == "2026-06-01"
    
    # 3. Consolidate sessions
    transformer.consolidate_sessions(is_champs=False)
    assert len(mock_template_data["session"]) == 1
    assert mock_template_data["session"][0]["SESSION"] == 1
    
    # 4. Scoring
    transformer.setup_scoring_and_seeding()
    scoring = mock_template_data["scoring"][0]
    assert scoring["Ind1"] == 5
    assert scoring["Rel1"] == 10

def test_ensure_team_exists_hermetic(mock_template_data):
    """Verify that ensure_team_exists adds teams when missing."""
    transformer = SeasonTransformer(mock_template_data)
    transformer.ensure_team_exists("CW", "Castlewood Barracudas")
    
    team_codes = [t.get("TCode") for t in mock_template_data["team"]]
    assert "CW" in team_codes
    assert any(t.get("TName") == "Castlewood Barracudas" for t in mock_template_data["team"])

@patch("mm_to_json.mm_to_json.MmToJsonConverter")
@patch("mm_to_json.mdb_restorer.restore_db")
def test_generate_season_logic_hermetic(mock_restore, mock_converter, mock_template_data):
    """Verify the high-level generation logic using mocks."""
    from generate_season import generate
    
    # Setup mock converter to return our template data
    instance = mock_converter.return_value
    instance.export_full_schema.return_value = {"tables": {tname: {"rows": rows, "columns": [], "indexes": []} for tname, rows in mock_template_data.items()}}
    
    # Run generate with mocks
    # We use a temporary directory for output to keep it hermetic
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock SCHEDULE_2026 for a single fast test run
        with patch("generate_season.SCHEDULE_2026", [{"date": "2026-05-30", "name": "FAST vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False, "opponent": "FAST"}]):
            generate("mock_template.mdb", tmpdir, owner_team="DP")
    
    # Verify that restore_db was called once
    assert mock_restore.called
    args, _ = mock_restore.call_args
    # args[0] is temp_json, args[1] is target_mdb
    assert "2026-05-30 FAST vs Del Prado.mdb" in args[1]
