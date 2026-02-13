import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Define a mock for meet_manager_pb2 if import fails (unlikely if protos generated)
try:
    import meet_manager_pb2

    from server import MeetManagerService
except ImportError:
    pytest.skip("Skipping because protos not generated", allow_module_level=True)


class TestUICorrectness:
    @pytest.fixture
    def service(self):
        with patch.object(MeetManagerService, "_load_data", return_value=None):
            with patch.object(MeetManagerService, "_load_config", return_value=None):
                svc = MeetManagerService()
                svc.config = {}  # Initialize manually since we mocked _load_config
                return svc

    def test_get_teams_athlete_count(self, service):
        service._data_cache = {
            "Team": [{"Team_no": "1", "Team_name": "Team A"}, {"Team_no": "2", "Team_name": "Team B"}],
            "Athlete": [
                {"Ath_no": "1", "Team_no": "1"},
                {"Ath_no": "2", "Team_no": "1"},
                {"Ath_no": "3", "Team_no": "2"},
            ],
        }

        response = service.GetTeams(None, None)
        assert len(response.teams) == 2

        team_a = next(t for t in response.teams if t.id == 1)
        assert team_a.athlete_count == 2

        team_b = next(t for t in response.teams if t.id == 2)
        assert team_b.athlete_count == 1

    def test_get_sessions_from_events(self, service):
        # Case 1: No Session table, infer from Events
        service._data_cache = {
            "Event": [
                {"Event_no": "1", "Sess_no": "1"},
                {"Event_no": "2", "Sess_no": "1"},
                {"Event_no": "3", "Sess_no": "2"},
            ],
            "Session": [],
        }

        response = service.GetSessions(None, None)
        assert len(response.sessions) == 2

        sess_1 = next(s for s in response.sessions if s.id == "1")
        assert sess_1.event_count == 2

        sess_2 = next(s for s in response.sessions if s.id == "2")
        assert sess_2.event_count == 1

    def test_get_sessions_default_all_events(self, service):
        # Case 2: No Session table, events have no Sess_no (default to 1) or all 1
        service._data_cache = {
            "Event": [
                {"Event_no": "1"},  # defaults to sess 1
                {"Event_no": "2"},
            ],
            "Session": [],
        }

        response = service.GetSessions(None, None)
        assert len(response.sessions) == 1
        assert response.sessions[0].name == "Session 1"
        assert response.sessions[0].event_count == 2

    def test_get_sessions_absolute_zero_data(self, service):
        # Case 3: No Events, No Sessions
        service._data_cache = {"Event": [], "Session": []}

        response = service.GetSessions(None, None)
        assert len(response.sessions) == 1
        assert response.sessions[0].name == "All Events"
        assert response.sessions[0].event_count == 0

    def test_admin_config_persistence(self, service):
        # Mock file writing
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            # Setup
            service.config = {"meet_name": "Old Name", "meet_description": "Old Desc"}

            # Update
            req = meet_manager_pb2.AdminConfig(meet_name="New Name", meet_description="New Desc")

            # Since we are mocking open, json.dump will write to the mock
            res = service.UpdateAdminConfig(req, None)

            assert res.meet_name == "New Name"
            assert service.config["meet_name"] == "New Name"

            # Verify file write was called
            mock_open.assert_called()
