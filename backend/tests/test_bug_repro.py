
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

try:
    from server import MeetManagerService
    import meet_manager_pb2
except ImportError:
    pytest.skip("Skipping because protos not generated", allow_module_level=True)

class TestBugReproduction:
    
    @pytest.fixture
    def service(self):
        with patch.object(MeetManagerService, '_load_data', return_value=None):
                svc = MeetManagerService()
                svc.config = {} 
                svc._scoring_map = None # Ensure no stale cache
                return svc

    def test_bug_1_entries_have_valid_ids(self, service):
        """Bug 1: Entries has an empty 'ID' column."""
        # Setup mock data
        service._data_cache = {
            'Entry': [
                {'Entry_no': '101', 'Event_ptr': '1', 'Ath_no': '1'},
                {'Entry_no': '102', 'Event_ptr': '1', 'Ath_no': '2'}
            ],
            'Athlete': [
                {'Ath_no': '1', 'First_name': 'A', 'Last_name': 'B', 'Team_no': '1'},
                {'Ath_no': '2', 'First_name': 'C', 'Last_name': 'D', 'Team_no': '1'}
            ],
            'Team': [{'Team_no': '1', 'Team_name': 'T1'}],
            'Event': [{'Event_no': '1', 'Event_sex': 'F', 'Event_dist': '50', 'Event_stroke': 'A'}]
        }
        
        response = service.GetEntries(None, None)
        assert len(response.entries) == 2
        
        # Verify IDs are populated and unique
        ids = [e.id for e in response.entries]
        assert all(isinstance(i, int) for i in ids)
        # Current implementation uses index, which IS an int, so this might pass even if bug exists in UI.
        # But if the UI expects a specific ID format or if 0 is considered "empty", we check.
        # Let's verify they are not all 0.
        assert len(set(ids)) == 2
        # If implementation uses `idx` from enumerate, it should be 0, 1. 

    def test_bug_2_events_entry_count(self, service):
        """Bug 2: Events has '0' for all of the Entries columns."""
        # Setup events and entries
        service._data_cache = {
            'Event': [
                {'Event_no': '1', 'Event_sex': 'F', 'Event_dist': '50', 'Event_stroke': 'A'},
                {'Event_no': '2', 'Event_sex': 'M', 'Event_dist': '100', 'Event_stroke': 'B'}
            ],
            'Entry': [
                {'Event_ptr': '1'}, {'Event_ptr': '1'}, # 2 entries for event 1
                {'Event_ptr': '2'}  # 1 entry for event 2
            ]
        }
        
        response = service.GetEvents(None, None)
        
        e1 = next(e for e in response.events if e.id == 1)
        e2 = next(e for e in response.events if e.id == 2)
        
        # This is expected to FAIL until we add entry_count to Proto and Server
        assert hasattr(e1, 'entry_count'), "Event proto missing entry_count field"
        assert e1.entry_count == 2
        assert e2.entry_count == 1

    def test_bug_3_sessions_date_and_events(self, service):
        """Bug 3: Sessions is missing 'Date' data and has '0' for all of its Events."""
        service._data_cache = {
             'Session': [
                 {'Sess_no': '1', 'Sess_date': '07/15/2025', 'Sess_name': 'Morning'},
             ],
             'Event': [
                 {'Event_no': '1', 'Sess_no': '1'},
                 {'Event_no': '2', 'Sess_no': '1'}
             ]
        }
        
        response = service.GetSessions(None, None)
        assert len(response.sessions) == 1
        s1 = response.sessions[0]
        
        assert s1.date == '07/15/2025'
        assert s1.event_count == 2
        
    def test_bug_4_meets_start_end_date(self, service):
        """Bug 4: Meets has empty 'Start Date' and 'End Date'."""
        service._data_cache = {
            'Meet': [
                {'Meet_name': 'Test Meet', 'Start': '07/15/2025', 'End': '07/17/2025'}
                # Note: MDB column names vary. Server uses 'Start_date' or 'Start'.
            ]
        }
        
        response = service.GetMeets(None, None)
        assert len(response.meets) == 1
        m = response.meets[0]
        
        assert m.start_date == '07/15/2025'
        assert m.end_date == '07/17/2025'

    def test_bug_5_scores_meet_context(self, service):
        """Bug 5: Scores > Team Scores shows '1' for the Meet column."""
        # Setup Scoring data (requires Teams, Scoring table, Athletes, Entries)
        # Actually GetScores calculates from Entry/Relay tables mostly, fallback to Scoring table.
        # The bug says "Shows '1' for the Meet column". Use GetMeets? 
        # No, "Scores > Team Scores". This is `GetScores`.
        # The Proto generic `Score` message doesn't have a "meet_name" field?
        # Let's check proto.
        # Message Score: team_id, team_name, points...
        # If UI shows a "Meet" column, it likely comes from somewhere.
        # Wait, the bug says "Shows '1' for the Meet column".
        # This implies the frontend is displaying a column "Meet" and it has value "1".
        # If it's the Meet ID, that explains "1".
        # We need to see if we can provide the Meet Name.
        
        service._data_cache = {
            'Team': [{'Team_no': '1', 'Team_name': 'Team A'}],
            'Entry': [{'Ath_no': '1', 'Event_ptr': '1', 'Ev_score': '5.0'}],
            'Athlete': [{'Ath_no': '1', 'Team_no': '1', 'Ath_Sex': 'F'}],
            'Event': [{'Event_no': '1', 'Event_sex': 'F'}],
            'Meet': [{'Meet_name': 'Championships'}]
        }
        service.config = {'meet_name': 'Configured Name'}
        
        response = service.GetScores(None, None)
        assert len(response.scores) > 0
        s = response.scores[0]
        
        # verify meet_name is populated from config
        assert s.meet_name == 'Configured Name'

    def test_bug_6_event_results_points(self, service):
        """Bug 6: Scores > Event Results is still missing all values for the Points column."""
        # Setup Entry with points
        service._data_cache = {
            'Entry': [{'Ath_no': '1', 'Event_ptr': '1', 'Ev_score': '9.0', 'Fin_place': '1'}],
            'Athlete': [{'Ath_no': '1', 'Team_no': '1', 'First_name':'A','Last_name':'B'}],
            'Team': [{'Team_no': '1', 'Team_name': 'Team A'}],
            'Event': [{'Event_no': '1', 'Event_sex': 'F'}]
        }
         
        response = service.GetEventScores(None, None)
        assert len(response.event_scores) == 1
        entries = response.event_scores[0].entries
        assert len(entries) == 1
        
        # Check points
        assert entries[0].points == 9.0

    def test_bug_7_athlete_teams_reload(self, service):
        """Bug 7: Athletes > Team drop down faceted filter doesn't look to be reloaded when datasets are changed."""
        # This is likely a Frontend caching issue or Backend not clearing cache?
        # Test Backend `SetActiveDataset` logic.
        
        # Initial state
        service.current_file = "A.json"
        service._data_cache = {'Team': [{'Team_no': '1', 'Team_name': 'Team A'}]}
        
        # Request switch
        # We need to mock _load_data to actually change the cache based on filename
        def side_effect():
            if service.current_file == "B.json":
                service._data_cache = {'Team': [{'Team_no': '2', 'Team_name': 'Team B'}]}
            else:
                 service._data_cache = {'Team': [{'Team_no': '1', 'Team_name': 'Team A'}]}
        
        with patch.object(service, '_load_data', side_effect=side_effect):
             with patch('os.path.exists', return_value=True): # Mock file exists
                req = MagicMock(filename="B.json")
                service.SetActiveDataset(req, MagicMock())
                
                # Verify cache updated via GetTeams
                resp = service.GetTeams(None, None)
                assert len(resp.teams) == 1
                assert resp.teams[0].name == "Team B"

