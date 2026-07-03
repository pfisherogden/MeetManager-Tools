import json
import os
import sys
from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest

# Add src to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    try:
        from meetmanager.v1 import meet_manager_pb2 as pb2
    except ImportError:
        import meet_manager_pb2 as pb2
except ImportError:
    pytest.skip("Protos not generated, skipping tests", allow_module_level=True)

from handlers.dq_handler import sync_dqs


class MockDQServicer:
    def __init__(self):
        self.storage = MagicMock()
        self._user_cache = OrderedDict()
        self._check_auth_val = "dev-user"
        self._config_val = {}
        self._data_val = ({}, {})

    def _check_auth(self, context):
        return self._check_auth_val

    def _load_user_config(self, context):
        return self._config_val

    def _load_user_data(self, context):
        return self._data_val

    def _get_table(self, cache, name):
        return cache.get(name, [])

    def _get_field(self, d, keys, default=None):
        for k in keys:
            if k in d:
                return d[k]
        return default

    def _safe_int(self, value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    def _mask_uid(self, uid):
        return f"masked-{uid}"

    def _mask_path(self, path):
        return f"masked-{path}"


def test_sync_dqs_isolated():
    servicer = MockDQServicer()
    servicer._config_val = {"active_dataset": "test_meet.mdb"}

    # Seeding event data
    servicer._data_val = (
        {
            "event": [
                {"event_no": "10", "event_ptr": 100, "Ind_rel": "I"},
                {"event_no": "20", "event_ptr": 200, "Ind_rel": "R"},
            ]
        },
        {},
    )

    mock_dqs = [
        {"event_id": 10, "swimmer_id": 123, "dq_code": "1A", "heat": 1, "lane": 2},
        {"event_id": 20, "swimmer_id": 456, "dq_code": "2B", "heat": 3, "lane": 4},
    ]

    request = pb2.SyncDQsRequest(dqs_json=json.dumps(mock_dqs), uid="dev-user", access_token="system-token")

    servicer.storage.exists.return_value = True

    with patch("mm_to_json.mdb_writer") as mock_mdb_writer:
        mock_db = MagicMock()
        mock_mdb_writer.open_db.return_value = mock_db
        mock_mdb_writer.update_entry_status.return_value = True

        with patch.dict(os.environ, {"DATA_ACCESS_TOKEN": "system-token"}):
            response = sync_dqs(request, None, servicer, pb2)

        assert response.success is True
        mock_mdb_writer.open_db.assert_called_once()
        mock_mdb_writer.update_entry_status.assert_any_call(
            mock_db, 100, 123, 1, 2, status="DQ", dq_code="1A", is_relay=False
        )
        mock_mdb_writer.update_entry_status.assert_any_call(
            mock_db, 200, 456, 3, 4, status="DQ", dq_code="2B", is_relay=True
        )
