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

from handlers.report_handler import generate_report, generate_report_bundle


class MockReportServicer:
    def __init__(self):
        self.storage = MagicMock()
        self.job_manager = MagicMock()
        self._user_cache = OrderedDict()
        self._check_auth_val = "dev-user"
        self._data_val = ({}, {"active_dataset": "Sample_Data.json"})

    def _check_auth(self, context):
        return self._check_auth_val

    def _load_user_data(self, context):
        return self._data_val


def test_generate_report_isolated():
    servicer = MockReportServicer()
    request = pb2.GenerateReportRequest(
        type=pb2.REPORT_TYPE_PSYCH_UNSPECIFIED,
        title="Test Psych Sheet",
    )

    with patch("handlers.report_handler._process_single_report_process") as mock_process:
        mock_process.return_value = {
            "success": True,
            "content": b"mock-pdf-content",
            "filename": "Test_Psych_Sheet.pdf",
            "rtype": "psych",
            "idx": 0,
            "load_duration": 0.1,
            "render_duration": 0.2,
        }

        with patch("mm_to_json.mm_to_json.MmToJsonConverter") as mock_converter:
            mock_instance = MagicMock()
            mock_converter.return_value = mock_instance
            mock_instance.convert.return_value = {}

            response = generate_report(request, None, servicer, pb2)

            assert response.success is True
            assert response.filename == "Test_Psych_Sheet.pdf"
            assert response.pdf_content == b"mock-pdf-content"


def test_generate_report_bundle_isolated():
    servicer = MockReportServicer()
    request = pb2.GenerateReportBundleRequest(
        reports=[
            pb2.GenerateReportRequest(type=pb2.REPORT_TYPE_PSYCH_UNSPECIFIED, title="Psych"),
        ]
    )

    servicer.job_manager.create_job.return_value = "mock-job-id"

    with patch("threading.Thread") as mock_thread:
        response = generate_report_bundle(request, None, servicer, pb2)

        assert response.success is True
        assert response.job_id == "mock-job-id"
        mock_thread.assert_called_once()
