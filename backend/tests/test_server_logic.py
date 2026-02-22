import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Define a mock for meet_manager_pb2 if import fails (unlikely if protos generated)
# But assuming they are there.

try:
    import meet_manager_pb2

    from server import MeetManagerService
except ImportError:
    # If not running in environment where protos are generated, we might fail
    pytest.skip("Skipping because protos not generated", allow_module_level=True)


def test_get_events_mapping():
    service = MeetManagerService()
    # Mock data
    service._data_cache = {
        "Event": [
            {
                "Event_no": "1",
                "Event_stroke": "A",
                "Event_sex": "M",
                "Event_dist": "50",
                "Low_age": "0",
                "High_Age": "0",
            },
            {
                "Event_no": "2",
                "Event_stroke": "E",
                "Event_sex": "F",
                "Event_dist": "200",
                "Ind_rel": "R",
            },  # Medley Relay
            {"Event_no": "3", "Event_stroke": "B ", "Event_sex": " G ", "Event_dist": "100"},  # Whitespace
        ]
    }

    # Patch _load_user_data to return our manual cache/config
    def mock_load_user_data(context):
        return service._data_cache, {}

    with patch.object(service, "_load_user_data", side_effect=mock_load_user_data):
        response = service.GetEvents(None, None)
        events = response.events

        assert len(events) == 3
        assert events[0].stroke == "Freestyle"
        assert events[0].gender == "Men"  # M -> Men

        assert events[1].stroke == "Medley Relay"
        assert events[1].gender == "Women"  # F -> Women

        assert events[2].stroke == "Backstroke"  # "B " -> "Backstroke"
        assert events[2].gender == "Girls"  # " G " -> "Girls"


def test_reload_on_upload():
    service = MeetManagerService()

    # Patch _save_user_config and _load_user_config to avoid actual storage
    with patch.object(service, "_save_user_config", return_value=None):
        with patch.object(service, "_load_user_config", return_value={}):
            # Simulate upload
            request = meet_manager_pb2.UploadRequest(filename="uploaded.mdb")

            # Mock file writing and storage upload
            with patch("builtins.open", new_callable=MagicMock):
                with patch.object(service.storage, "upload_file", return_value=None):
                    with patch.object(service, "_check_auth", return_value="dev-user"):
                        service.UploadDataset(iter([request]), None)
