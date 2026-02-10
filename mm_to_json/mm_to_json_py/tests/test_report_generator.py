import pytest
import os
import tempfile
from mm_to_json.report_generator import ReportGenerator

@pytest.fixture
def mock_meet_data():
    return {
        "meetName": "Test Cup 2026",
        "meetStart": "2026-06-01",
        "meetEnd": "2026-06-02",
        "sessions": [
            {
                "events": [
                    {
                        "eventNum": "1",
                        "eventDesc": "Mixed 50 Free",
                        "entries": [
                            {
                                "lane": "1",
                                "name": "Alice Smith",
                                "age": "10",
                                "team": "Sharks",
                                "seedTime": "30.50",
                                "heat": "1",
                                "place": "1",
                                "finalTime": "30.10",
                                "points": "10"
                            },
                            {
                                "lane": "2",
                                "name": "Bob Jones",
                                "age": "11",
                                "team": "Dolphins",
                                "seedTime": "32.00",
                                "heat": "1",
                                "place": "2",
                                "finalTime": "31.50",
                                "points": "8"
                            }
                        ]
                    }
                ]
            }
        ]
    }

def test_generate_psych_sheet(mock_meet_data):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = tmp.name
    
    try:
        rg = ReportGenerator(mock_meet_data, title="Psych Sheet Test")
        rg.generate_psych_sheet(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_generate_meet_entries(mock_meet_data):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = tmp.name
    
    try:
        rg = ReportGenerator(mock_meet_data, title="Entries Test")
        rg.generate_meet_entries(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_generate_lineup_sheets(mock_meet_data):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = tmp.name
    
    try:
        rg = ReportGenerator(mock_meet_data, title="Lineup Test")
        rg.generate_lineup_sheets(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_generate_meet_results(mock_meet_data):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = tmp.name
    
    try:
        rg = ReportGenerator(mock_meet_data, title="Results Test")
        rg.generate_meet_results(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(path):
            os.remove(path)
