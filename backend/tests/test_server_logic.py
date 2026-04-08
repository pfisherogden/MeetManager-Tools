import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Define a mock for meet_manager_pb2 if import fails (unlikely if protos generated)
# But assuming they are there.

try:
    try:
        from meetmanager.v1 import meet_manager_pb2
    except ImportError:
        import meet_manager_pb2

    from server import MeetManagerService
except ImportError:
    # If not running in environment where protos are generated, we might fail
    pytest.skip("Skipping because protos not generated", allow_module_level=True)


def test_get_events_mapping():
    service = MeetManagerService()
    # Mock data
    service._data_cache = {
        "event": [
            {
                "event_no": "1",
                "event_stroke": "A",
                "event_sex": "M",
                "event_dist": "50",
                "low_age": "0",
                "high_age": "0",
            },
            {
                "event_no": "2",
                "event_stroke": "E",
                "event_sex": "F",
                "event_dist": "200",
                "ind_rel": "R",
            },  # Medley Relay
            {"event_no": "3", "event_stroke": "B ", "event_sex": " G ", "event_dist": "100"},  # Whitespace
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
            request = meet_manager_pb2.UploadDatasetRequest(filename="uploaded.mdb")

            # Mock file writing and storage upload
            with patch("builtins.open", new_callable=MagicMock):
                with patch.object(service.storage, "upload_file", return_value=None):
                    with patch.object(service, "_check_auth", return_value="dev-user"):
                        service.UploadDataset(iter([request]), None)


def test_sync_dqs_logic():
    from collections import OrderedDict
    service = MeetManagerService()
    # Mock cache with event mapping
    service._user_cache = OrderedDict({
        "dev-user": {
            "filename": "test.mdb",
            "mtime": 123456789,
            "data": {
                "event": [
                    {"event_no": "10", "event_ptr": 100, "Ind_rel": "I"},
                    {"event_no": "20", "event_ptr": 200, "Ind_rel": "R"},
                ]
            }
        }
    })

    mock_config = {"active_dataset": "test.mdb"}
    mock_dqs = [
        {"event_id": 10, "swimmer_id": 123, "dq_code": "1A", "heat": 1, "lane": 2},
        {"event_id": 20, "swimmer_id": 456, "dq_code": "2B", "heat": 3, "lane": 4},
    ]

    with patch.object(service, "_check_auth", return_value="dev-user"):
        with patch.object(service, "_load_user_config", return_value=mock_config):
            with patch.object(service, "_load_user_data", return_value=(service._user_cache["dev-user"]["data"], {})):
                with patch.object(service, "storage") as mock_storage:
                    mock_storage.exists.return_value = True
                    # Mock mdb_writer
                    with patch("mm_to_json.mdb_writer") as mock_mdb_writer:
                        mock_db = MagicMock()
                        mock_mdb_writer.open_db.return_value = mock_db
                        mock_mdb_writer.update_entry_status.return_value = True

                        request = meet_manager_pb2.SyncDQsRequest(dqs_json=json.dumps(mock_dqs))
                        response = service.SyncDQs(request, None)

                        assert response.success is True
                    # Verify event 10 (Individual)
                    mock_mdb_writer.update_entry_status.assert_any_call(
                        mock_db, 100, 123, 1, 2, status="DQ", dq_code="1A", is_relay=False
                    )
                    # Verify event 20 (Relay)
                    mock_mdb_writer.update_entry_status.assert_any_call(
                        mock_db, 200, 456, 3, 4, status="DQ", dq_code="2B", is_relay=True
                    )
                    assert mock_mdb_writer.update_entry_status.call_count == 2
