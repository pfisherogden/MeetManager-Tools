import os
import sys
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

from handlers.publish_handler import publish_meet_data


class MockPublishServicer:
    def __init__(self):
        self.storage = MagicMock()
        self._check_auth_val = "dev-user"
        self._data_val = ({}, {"active_dataset": "Sample_Data.json"})

    def _check_auth(self, context):
        return self._check_auth_val

    def _load_user_data(self, context):
        return self._data_val


def test_publish_meet_data_isolated():
    servicer = MockPublishServicer()
    request = pb2.PublishMeetDataRequest(frontend_url="http://localhost:3000")

    with patch("mm_to_json.mm_to_json.MmToJsonConverter") as mock_converter:
        mock_instance = MagicMock()
        mock_converter.return_value = mock_instance
        mock_instance.convert.return_value = {"sessions": []}

        with patch("mm_to_json.judge_app_extractor.JudgeAppExtractor") as mock_extractor:
            mock_ext_instance = MagicMock()
            mock_extractor.return_value = mock_ext_instance
            mock_ext_instance.extract_judge_data.return_value = {"events": []}

            with patch.dict(os.environ, {"DATA_ACCESS_TOKEN": "system-token"}):
                response = publish_meet_data(request, None, servicer, pb2)

            assert response.success is True
            assert "/judge" in response.judge_app_url
            servicer.storage.upload_file.assert_called_once()
