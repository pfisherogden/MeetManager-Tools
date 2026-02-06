import pytest
import json
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from server import MeetManagerService

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

class MockMeetManagerService(MeetManagerService):
    def __init__(self):
        self._data_cache = {}
        for name in ['Relay', 'RelayNames', 'Entry', 'Event', 'Session', 'Team', 'Scoring', 'Athlete']:
            try:
                with open(os.path.join(FIXTURES_DIR, f"{name}.json")) as f:
                    self._data_cache[name] = json.load(f)
            except FileNotFoundError:
                self._data_cache[name] = []

    def _get_table(self, table_name):
        return self._data_cache.get(table_name, [])

@pytest.fixture
def service():
    return MockMeetManagerService()

def test_entry_mapping_completeness(service):
    """Verify that entries have all required fields for UI display and filtering."""
    resp = service.GetEntries(None, None)
    assert len(resp.entries) > 0
    
    # We want to see at least some real data for these
    has_heat = False
    has_lane = False
    has_points = False
    has_event_name = False
    has_athlete_name = False
    
    for e in resp.entries:
        if e.heat > 0: has_heat = True
        if e.lane > 0: has_lane = True
        if e.points > 0: has_points = True
        if len(e.event_name) > 5: has_event_name = True
        if len(e.athlete_name) > 2: has_athlete_name = True
        
        # Every entry MUST have these
        assert e.id is not None
        assert e.event_id > 0
        assert e.athlete_id > 0
        
    assert has_heat, "Critical Mapping Failure: No entries have Heat data"
    assert has_lane, "Critical Mapping Failure: No entries have Lane data"
    assert has_points, "Critical Mapping Failure: No entries have Points data"
    assert has_event_name, "Critical Mapping Failure: No entries have valid Event Name"
    assert has_athlete_name, "Critical Mapping Failure: No entries have valid Athlete Name"

def test_relay_mapping_completeness(service):
    """Verify relays have all legs and event metadata."""
    resp = service.GetRelays(None, None)
    assert len(resp.relays) > 0
    
    has_legs = False
    has_event_name = False
    has_final_time = False
    
    for r in resp.relays:
        if r.leg1_name and r.leg2_name and r.leg3_name and r.leg4_name:
            has_legs = True
        if len(r.event_name) > 5:
            has_event_name = True
        if r.final_time and r.final_time != "NT":
            has_final_time = True
            
    assert has_legs, "Critical Mapping Failure: No relays have all 4 leg names"
    assert has_event_name, "Critical Mapping Failure: No relays have valid Event Name"
    assert has_final_time, "Critical Mapping Failure: No relays have results (final_time)"

def test_athlete_mapping_completeness(service):
    """Verify athletes have gender and team info for faceted filtering."""
    resp = service.GetAthletes(None, None)
    assert len(resp.athletes) > 0
    
    has_gender = False
    has_dob = False
    has_team = False
    
    for a in resp.athletes:
        if a.gender in ['M', 'F']: has_gender = True
        if a.date_of_birth and len(a.date_of_birth) > 5: has_dob = True
        if a.team_name and len(a.team_name) > 2: has_team = True
        
    assert has_gender, "Critical Mapping Failure: No athletes have M/F gender"
    assert has_dob, "Critical Mapping Failure: No athletes have valid Date of Birth"
    assert has_team, "Critical Mapping Failure: No athletes have Team names"

def test_event_mapping_filters(service):
    """Verify events have stroke and gender for filtering."""
    resp = service.GetEvents(None, None)
    assert len(resp.events) > 0
    
    has_stroke = False
    has_gender = False
    
    for e in resp.events:
        if e.stroke and len(e.stroke) > 2: has_stroke = True
        if e.gender and len(e.gender) >= 1: has_gender = True
        
    assert has_stroke, "Critical Mapping Failure: No events have valid Stroke"
    assert has_gender, "Critical Mapping Failure: No events have valid Gender populated"
