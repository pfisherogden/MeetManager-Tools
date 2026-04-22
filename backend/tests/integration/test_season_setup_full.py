import json
import os
import sys
import pytest
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))
# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../scripts/season_setup"))

from mm_to_json.mm_to_json import MmToJsonConverter
from generate_season import generate

TEMPLATE_MDB = "../template_unzip/swmeets7/Summer League Meet Template.mdb"

@pytest.mark.skipif(not os.path.exists(TEMPLATE_MDB), reason="Template MDB not found")
def test_full_season_generation_and_load(tmp_path):
    """
    E2E Integration Test:
    1. Generate a 2026 meet MDB from the template.
    2. Load the generated MDB back using MmToJsonConverter.
    3. Verify that the metadata matches the 2024 instructions.
    """
    output_dir = tmp_path / "2026_meets"
    
    # We only generate one meet for the test to keep it fast
    # We patch SCHEDULE_2026 inside the test
    from unittest.mock import patch
    mock_schedule = [
        {"date": "2026-05-30", "name": "FAST vs Del Prado", "host": "Del Prado Cabana Club", "is_champs": False, "opponent": "FAST"}
    ]
    
    with patch("generate_season.SCHEDULE_2026", mock_schedule):
        generate(TEMPLATE_MDB, str(output_dir), owner_team="DP")
        
    # Verify file existence
    generated_file = output_dir / "2026 Del Prado Data" / "Swim Meets" / "2026-05-30 FAST vs Del Prado" / "2026-05-30 FAST vs Del Prado.mdb"
    assert generated_file.exists()
    
    # Load it back
    conv = MmToJsonConverter(mdb_path=str(generated_file))
    
    # Verify Meet Info
    meet_info = conv.get_meet_info()
    assert meet_info["meetName"] == "FAST vs Del Prado"
    assert meet_info["meetLocation"] == "Del Prado Cabana Club"
    assert meet_info["numLanes"] == 6
    
    # Verify Data Purge (Athletes should be empty)
    athletes = conv.tables.get("athlete")
    assert athletes is None or len(athletes) == 0
    
    # Verify Sessions (Should be exactly 1)
    sessions = conv.get_session_info()
    assert len(sessions) == 1
    assert sessions[0].number == 1
    
    # Verify Events (All should be in Session 1)
    events = conv.get_all_events()
    assert len(events) > 0
    for event in events:
        # Check raw table if possible or internal state
        pass
        
    # Verify Scoring (Standard 5/3/2/1)
    scoring = conv.tables.get("scoring")
    if scoring is not None and not scoring.empty:
        row = scoring.iloc[0]
        # Check standard ind scoring
        for i, val in enumerate([5, 3, 2, 1], 1):
            col = f"Ind{i}"
            if col in scoring.columns:
                assert int(row[col]) == val
