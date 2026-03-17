import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Define a mock for meet_manager_pb2 if import fails (unlikely if protos generated)
try:
    try:
        from meetmanager.v1 import meet_manager_pb2
    except ImportError:
        import meet_manager_pb2

    from server import MeetManagerService
except ImportError:
    pytest.skip("Skipping because protos not generated", allow_module_level=True)


class TestUICorrectness:
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

    def test_get_teams_athlete_count(self, service):
        service._data_cache = {
            "team": [{"team_no": "1", "team_name": "Team A"}, {"team_no": "2", "team_name": "Team B"}],
            "athlete": [
                {"ath_no": "1", "team_no": "1"},
                {"ath_no": "2", "team_no": "1"},
                {"ath_no": "3", "team_no": "2"},
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
            "event": [
                {"event_no": "1", "sess_no": "1"},
                {"event_no": "2", "sess_no": "1"},
                {"event_no": "3", "sess_no": "2"},
            ],
            "session": [],
        }

        response = service.GetSessions(None, None)
        assert len(response.sessions) == 2

        sess_1 = next(s for s in response.sessions if s.id == "1")
        assert sess_1.event_count == 2

        sess_2 = next(s for s in response.sessions if s.id == "2")
        assert sess_2.event_count == 1

    def test_get_sessions_default_all_events(self, service):
        # Case 2: No Session table, events have no sess_no (default to 1) or all 1
        service._data_cache = {
            "event": [
                {"event_no": "1"},  # defaults to sess 1
                {"event_no": "2"},
            ],
            "session": [],
        }

        response = service.GetSessions(None, None)
        assert len(response.sessions) == 1
        assert response.sessions[0].name == "Session 1"
        assert response.sessions[0].event_count == 2

    def test_get_sessions_absolute_zero_data(self, service):
        # Case 3: No Events, No Sessions
        service._data_cache = {"event": [], "session": []}

        response = service.GetSessions(None, None)
        assert len(response.sessions) == 1
        assert response.sessions[0].name == "Session 1"
        assert response.sessions[0].event_count == 0

    def test_admin_config_persistence(self, service):
        # Setup
        initial_config = {"meet_name": "Old Name", "meet_description": "Old Desc"}

        with patch.object(service, "_load_user_config", return_value=initial_config):
            with patch.object(service, "_save_user_config", return_value=None) as mock_save:
                # Update
                req = meet_manager_pb2.UpdateAdminConfigRequest(meet_name="New Name", meet_description="New Desc")
                mock_context = MagicMock()
                mock_context.uid = "test-user"

                res = service.UpdateAdminConfig(req, mock_context)

                assert res.meet_name == "New Name"
                # Verify save was called with updated config
                mock_save.assert_called_once()
                args, _ = mock_save.call_args
                assert args[1]["meet_name"] == "New Name"
