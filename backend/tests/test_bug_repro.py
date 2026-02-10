
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
                svc._scoring_map = None 
                return svc

    def test_bug_1_entries_have_valid_ids(self, service):
        """Bug 1: Entries has an empty 'ID' column (now using Entry_no)."""
        service._data_cache = {
            'Entry': [
                {'Entry_no': '101', 'Event_ptr': '1', 'Ath_no': '1', 'Team_no': '1'},
                {'Entry_no': '102', 'Event_ptr': '1', 'Ath_no': '2', 'Team_no': '1'}
            ],
            'Athlete': [{'Ath_no': '1', 'First_name': 'A', 'Last_name': 'B', 'Team_no': '1'}],
            'Team': [{'Team_no': '1', 'Team_name': 'T1'}],
            'Event': [{'Event_no': '1'}]
        }
        
        response = service.GetEntries(None, None)
        assert len(response.entries) == 2
        # Verify IDs are populated from Entry_no
        assert response.entries[0].id == 101
        assert response.entries[1].id == 102

    def test_bug_2_events_entry_count(self, service):
        """Bug 2: Events has '0' for all of the Entries columns."""
        service._data_cache = {
            'Event': [
                {'Event_no': '1', 'Event_sex': 'F', 'Event_dist': '50', 'Event_stroke': 'A'},
                {'Event_no': '2', 'Event_sex': 'M', 'Event_dist': '100', 'Event_stroke': 'B'}
            ],
            'Entry': [
                {'Event_ptr': '1'}, {'Event_ptr': '1'}, 
                {'Event_ptr': '2'}
            ]
        }
        
        response = service.GetEvents(None, None)
        
        e1 = next(e for e in response.events if e.id == 1)
        e2 = next(e for e in response.events if e.id == 2)
        
        assert hasattr(e1, 'entry_count')
        assert e1.entry_count == 2
        assert e2.entry_count == 1

    def test_bug_3_sessions_date_and_events(self, service):
        """Bug 3: Sessions is missing 'Date' data and has '0' for all of its Events."""
        service._data_cache = {
             'Session': [
                 {'Sess_no': '1', 'Sess_day': '1', 'Sess_name': 'Morning'},
             ],
             'Event': [
                 {'Event_no': '1', 'Sess_no': '1'},
                 {'Event_no': '2', 'Sess_no': '1'}
             ],
             'Meet': [{'Start': '07/12/25'}]
        }
        
        response = service.GetSessions(None, None)
        assert len(response.sessions) == 1
        s1 = response.sessions[0]
        
        # Date derived from Meet Start (07/12/25) + Day 1 = 2025-07-12
        assert '2025-07-12' in s1.date 
        assert s1.event_count == 2
        
    def test_bug_4_meets_start_end_date(self, service):
        """Bug 4: Meets has empty 'Start Date' and 'End Date'."""
        service._data_cache = {
            'Meet': [
                {'Meet_name': 'Test Meet', 'Start': '07/15/2025', 'End': '07/17/2025'}
            ]
        }
        
        response = service.GetMeets(None, None)
        assert len(response.meets) == 1
        m = response.meets[0]
        
        assert m.start_date == '2025-07-15'
        assert m.end_date == '2025-07-17'

    def test_bug_5_scores_meet_context(self, service):
        """Bug 5: Scores > Team Scores shows '1' for the Meet column."""
        service._data_cache = {
            'Team': [{'Team_no': '1', 'Team_name': 'Team A'}],
            'Entry': [{'Ath_no': '1', 'Event_ptr': '1', 'Ev_score': '5.0', 'Team_no': '1'}],
            'Athlete': [{'Ath_no': '1', 'Team_no': '1', 'Ath_Sex': 'F'}],
            'Event': [{'Event_no': '1', 'Event_sex': 'F'}],
            'Meet': [{'Meet_name': 'Championships'}]
        }
        service.config = {'meet_name': 'Championships'}
        
        response = service.GetScores(None, None)
        assert len(response.scores) > 0
        s = response.scores[0]
        
        assert s.meet_name == 'Championships'

    def test_bug_6_event_results_points(self, service):
        """Bug 6: Scores > Event Results is still missing all values for the Points column."""
        # Setup Scoring table logic verification
        # Case A: Explicit points in Ev_score
        service._data_cache = {
            'Entry': [{'Ath_no': '1', 'Event_ptr': '1', 'Ev_score': '9.0', 'Fin_place': '1'}],
            'Athlete': [{'Ath_no': '1', 'Team_no': '1', 'First_name':'A','Last_name':'B'}],
            'Team': [{'Team_no': '1', 'Team_name': 'Team A'}],
            'Event': [{'Event_no': '1', 'Event_sex': 'F'}],
            'Scoring': []
        }
        service._scoring_map = None # Clear cache
         
        response = service.GetEventScores(None, None)
        entries = response.event_scores[0].entries
        assert entries[0].points == 9.0

