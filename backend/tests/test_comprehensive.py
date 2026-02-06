
import pytest
import json
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from server import MeetManagerService

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

class MockContext:
    def set_code(self, code): pass
    def set_details(self, details): pass

class MockMeetManagerService(MeetManagerService):
    def __init__(self):
        self._data_cache = {}
        # Load fixtures into cache
        for name in ['Relay', 'RelayNames', 'Entry', 'Event', 'Session', 'Team', 'Scoring', 'Athlete']:
            try:
                with open(os.path.join(FIXTURES_DIR, f"{name}.json")) as f:
                    self._data_cache[name] = json.load(f)
            except FileNotFoundError:
                print(f"Fixture {name}.json not found")
                self._data_cache[name] = []

    def _get_table(self, table_name):
        return self._data_cache.get(table_name, [])

@pytest.fixture
def service():
    return MockMeetManagerService()

def test_athletes_birthdate(service):
    """(5) Athletes should have individual birthdates, not identical ones."""
    resp = service.GetAthletes(None, None)
    assert len(resp.athletes) > 0
    
    # Collect birthdates
    dobs = set()
    for ath in resp.athletes:
        if ath.date_of_birth:
            dobs.add(ath.date_of_birth)
            
    # Should have multiple different birthdates
    assert len(dobs) > 1, "All athletes have the same or no birthdate!"
    print(f"Found {len(dobs)} unique birthdates among {len(resp.athletes)} athletes")

def test_entries_fields(service):
    """(4) Entries should have ID, Final Time, Place, Event Name, Heat, and Lane."""
    resp = service.GetEntries(None, None)
    assert len(resp.entries) > 0
    
    missing_data = 0
    has_heats = False
    has_lanes = False
    has_points = False
    
    for e in resp.entries:
        assert e.id is not None
        
        if not e.event_name:
            missing_data += 1
            
        if e.heat > 0:
            has_heats = True
        if e.lane > 0:
            has_lanes = True
        if e.points > 0:
            has_points = True
             
    assert missing_data == 0, "Some entries are missing event_name"
    assert has_heats, "No entries have heat data"
    assert has_lanes, "No entries have lane data"
    assert has_points, "No entries have points data"

def test_relays_fields(service):
    """(1, 3, 8) Relays should have Event Name, Final Time, Place, Leg Names."""
    resp = service.GetRelays(None, None)
    assert len(resp.relays) > 0
    
    has_legs = False
    has_event_name = False
    has_final = False
    has_place = False
    
    for r in resp.relays:
        if r.leg1_name:
            has_legs = True
        if r.event_name:
            has_event_name = True
        if r.final_time:
            has_final = True
        if r.place > 0:
            has_place = True
        
    assert has_legs, "No relays have leg names"
    assert has_event_name, "No relays have event name"
    assert has_final, "No relays have final time"
    # Place might be 0 if not scored or DQ, but in this file there are results
    assert has_place, "No relays have place rank"

def test_nt_validity(service):
    """(2) NT is a valid seed time."""
    # Inject mock entries into the service's cache to robustness test the logic
    mock_entries = [
        {'Event_ptr': '1', 'Ath_no': '1', 'ActualSeed_time': '0.00', 'Seed_Time': '0'},
        {'Event_ptr': '1', 'Ath_no': '2', 'ActualSeed_time': '', 'Seed_Time': ''},
        {'Event_ptr': '1', 'Ath_no': '3', 'ActualSeed_time': 'NT', 'Seed_Time': 'NT'},
    ]
    # Access private cache for testing
    service._data_cache['Entry'] = mock_entries + service._data_cache['Entry']
    
    resp = service.GetEntries(None, None)
    
    nt_count = 0
    for e in resp.entries:
        if e.seed_time == 'NT':
            nt_count += 1
            
    # We injected 3 cases that should result in NT
    # (plus potentially any real ones, but at least 3)
    assert nt_count >= 3, f"Expected at least 3 NT entries, found {nt_count}"

def test_event_scores(service):
    """(7) Scores for each event."""
    # Assuming GetEventScores is implemented
    if not hasattr(service, 'GetEventScores'):
        pytest.fail("GetEventScores RPC not implemented in server class")
        
    resp = service.GetEventScores(None, None)
    assert len(resp.event_scores) > 0
    
    # Check structure
    ev1 = resp.event_scores[0]
    assert ev1.event_name
    assert len(ev1.entries) > 0
    
    # Check that entries inside have ranks/names
    ent = ev1.entries[0]
    assert ent.athlete_name or ent.team_name or ent.athlete_id == 0 # Relay case
    
    # Check points (optional, but good to check field exists)
    assert hasattr(ent, 'points')
    
def test_teams_athlete_count(service):
    """(6) Check athlete count is populated (Hyperlink verify is UI test, but backend data needed)."""
    resp = service.GetTeams(None, None)
    assert len(resp.teams) > 0
    
    has_count = False
    for t in resp.teams:
        if t.athlete_count > 0:
            has_count = True
            break
    assert has_count

