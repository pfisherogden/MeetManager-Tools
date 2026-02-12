import os
import json
import pytest
import pandas as pd
import sys

# Add backend/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/src")))

from mm_to_json.mm_to_json import MmToJsonConverter

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../fixtures/anonymized_meets"))

def get_anonymized_fixtures():
    fixtures = []
    if os.path.exists(FIXTURES_DIR):
        for f in os.listdir(FIXTURES_DIR):
            if f.endswith(".json"):
                fixtures.append(os.path.join(FIXTURES_DIR, f))
    return fixtures

@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_converter_extraction(fixture_path):
    with open(fixture_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    table_data = fixture_wrapper["data"]
    metadata = fixture_wrapper["metadata"]
    
    converter = MmToJsonConverter(table_data=table_data)
    
    # Verify logical tables were loaded
    assert len(converter.tables) > 0
    assert "Meet" in converter.tables
    assert "Athlete" in converter.tables
    assert "Team" in converter.tables
    assert "Event" in converter.tables
    
    # Check athletes
    # Note: converter.tables["Athlete"] is a DataFrame
    ath_df = converter.tables["Athlete"]
    assert len(ath_df) > 0
    
    # Check that schema_type was correctly identified
    assert converter.schema_type == metadata["schema_type"]

def test_nan_handling():
    # Test specific fix for "nan" team names
    table_data = {
        "TEAM": [
            {"Team": 1, "TCode": "TST", "TName": float('nan'), "Short": "Test"}
        ],
        "MEET": [{"Meet": 1, "MName": "Test Meet"}]
    }
    converter = MmToJsonConverter(table_data=table_data)
    team_df = converter.tables.get("Team")
    assert not team_df.empty
    
    # Verify that the team name is handled safely
    row = team_df.iloc[0]
    # In mm_to_json, it uses _get_val which should return "" for NaN
    val = converter._get_val(row, "TName")
    assert val == ""

def test_athlete_date_format():
    # Ensure birthdates are strings or handled consistently
    table_data = {
        "ATHLETE": [
            {"Ath_no": 1, "First_name": "Joe", "Last_name": "Swim", "Birth_date": "2010-01-01 00:00:00"}
        ],
        "MEET": [{"Meet": 1, "MName": "Test"}]
    }
    converter = MmToJsonConverter(table_data=table_data)
    ath_df = converter.tables.get("Athlete")
    row = ath_df.iloc[0]
    dob = converter._get_val(row, "Birth_date")
    assert "2010-01-01" in dob
