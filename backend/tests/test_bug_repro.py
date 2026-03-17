import os
import sys
from unittest.mock import patch

import pytest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    from server import MeetManagerService
except ImportError:
    pytest.skip("Skipping because protos not generated", allow_module_level=True)


class TestBugReproduction:
    @pytest.fixture
    def service(self):
        svc = MeetManagerService()
        svc.config = {}
        svc._data_cache = {}

        # Patch _load_user_data to return our manual cache/config
        def mock_load_user_data(context):
            return svc._data_cache, svc.config

        with patch.object(svc, "_load_user_data", side_effect=mock_load_user_data):
            yield svc

    def test_bug_1_entries_have_valid_ids(self, service):
        """Bug 1: Entries has an empty 'ID' column (now using entry_no)."""
        service._data_cache = {
            "entry": [
                {"entry_no": "101", "event_ptr": "1", "ath_no": "1", "team_no": "1"},
                {"entry_no": "102", "event_ptr": "1", "ath_no": "2", "team_no": "1"},
            ],
            "athlete": [{"ath_no": "1", "first_name": "A", "last_name": "B", "team_no": "1"}],
            "team": [{"team_no": "1", "team_name": "T1"}],
            "event": [{"event_no": "1"}],
        }

        response = service.GetEntries(None, None)
        assert len(response.entries) == 2
        # Verify IDs are populated from entry_no
        assert response.entries[0].id == 101
        assert response.entries[1].id == 102

    def test_bug_2_events_entry_count(self, service):
        """Bug 2: Events has '0' for all of the Entries columns."""
        service._data_cache = {
            "event": [
                {"event_no": "1", "event_sex": "F", "event_dist": "50", "event_stroke": "A"},
                {"event_no": "2", "event_sex": "M", "event_dist": "100", "event_stroke": "B"},
            ],
            "entry": [{"event_ptr": "1"}, {"event_ptr": "1"}, {"event_ptr": "2"}],
        }

        response = service.GetEvents(None, None)

        e1 = next(e for e in response.events if e.id == 1)
        e2 = next(e for e in response.events if e.id == 2)

        assert hasattr(e1, "entry_count")
        assert e1.entry_count == 2
        assert e2.entry_count == 1

    def test_bug_3_sessions_date_and_events(self, service):
        """Bug 3: Sessions is missing 'Date' data and has '0' for all of its Events."""
        service._data_cache = {
            "session": [
                {"sess_no": "1", "sess_day": "1", "sess_name": "Morning"},
            ],
            "event": [{"event_no": "1", "sess_no": "1"}, {"event_no": "2", "sess_no": "1"}],
            "meet": [{"start": "07/12/25"}],
        }

        response = service.GetSessions(None, None)
        assert len(response.sessions) == 1
        s1 = response.sessions[0]

        # Date derived from Meet start (07/12/25) + Day 1 = 2025-07-12
        assert "2025-07-12" in s1.date
        assert s1.event_count == 2

    def test_bug_4_meets_start_end_date(self, service):
        """Bug 4: Meets has empty 'Start Date' and 'End Date'."""
        service._data_cache = {"meet": [{"meet_name": "Test Meet", "start": "07/15/2025", "end": "07/17/2025"}]}

        response = service.GetMeets(None, None)
        assert len(response.meets) == 1
        m = response.meets[0]

        assert m.start_date == "2025-07-15"
        assert m.end_date == "2025-07-17"

    def test_bug_5_scores_meet_context(self, service):
        """Bug 5: Scores > Team Scores shows '1' for the Meet column."""
        service._data_cache = {
            "team": [{"team_no": "1", "team_name": "Team A"}],
            "entry": [{"ath_no": "1", "event_ptr": "1", "ev_score": "5.0", "team_no": "1"}],
            "athlete": [{"ath_no": "1", "team_no": "1", "ath_sex": "F"}],
            "event": [{"event_no": "1", "event_sex": "F"}],
            "meet": [{"meet_name": "Championships"}],
        }
        service.config = {"meet_name": "Championships"}

        response = service.GetScores(None, None)
        assert len(response.scores) > 0
        s = response.scores[0]

        assert s.meet_name == "Championships"

    def test_bug_6_event_results_points(self, service):
        """Bug 6: Scores > Event Results is still missing all values for the Points column."""
        # Setup Scoring table logic verification
        # Case A: Explicit points in ev_score
        service._data_cache = {
            "entry": [{"ath_no": "1", "event_ptr": "1", "ev_score": "9.0", "fin_place": "1"}],
            "athlete": [{"ath_no": "1", "team_no": "1", "first_name": "A", "last_name": "B"}],
            "team": [{"team_no": "1", "team_name": "Team A"}],
            "event": [{"event_no": "1", "event_sex": "F"}],
            "scoring": [],
        }
        service._scoring_map = None  # Clear cache

        response = service.GetEventScores(None, None)
        entries = response.event_scores[0].entries
        assert entries[0].points == 9.0
