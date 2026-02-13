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
    # Patch _load_data to avoid file access during init
    with patch.object(MeetManagerService, "_load_data", return_value=None):
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
    with patch.object(MeetManagerService, "_load_data", return_value=None) as mock_load:
        service = MeetManagerService()
        service.current_file = "uploaded.mdb"

        # Reset mock from init call
        mock_load.reset_mock()

        # Simulate upload of uploaded.mdb
        # We need a generator for request_iterator
        request = meet_manager_pb2.UploadRequest(filename="uploaded.mdb")

        # Mock file writing
        with patch("builtins.open", new_callable=MagicMock):
            service.UploadDataset(iter([request]), None)

        mock_load.assert_called_once()
