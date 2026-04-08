import os
import time
import urllib.parse

import grpc
import pytest
import requests

from meetmanager.v1 import meet_manager_pb2 as pb2
from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc

# Skip all tests in this module if not in CI
# Integration tests require live services
pytestmark = pytest.mark.skipif(
    not os.environ.get("CI") and not os.environ.get("RUN_INTEGRATION"),
    reason="Integration tests require live services or RUN_INTEGRATION=1",
)

GRPC_PORT = os.getenv("BACKEND_PORT", "8081")
GRPC_TARGET = os.getenv("TEST_GRPC_TARGET", f"127.0.0.1:{8080 if os.path.exists('/.dockerenv') else GRPC_PORT}")
WEB_TARGET = os.getenv("TEST_WEB_TARGET", f"http://{'frontend' if os.path.exists('/.dockerenv') else 'localhost'}:3000")


@pytest.fixture(scope="module")
def grpc_stub():
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = pb2_grpc.MeetManagerServiceStub(channel)
    return stub


def test_dq_sync_e2e_flow(grpc_stub):
    """
    End-to-End Test:
    1. Upload MDB.
    2. Publish for Judge App (Verify production URLs and encoding).
    3. Simulate Judge App submitting a DQ via stateless API.
    4. Verify DQ is persisted in MDB via GetEntries gRPC call.
    """
    # --- 1. Upload MDB ---
    potential_mdbs = ["/app/tmp/sample_data_champs_2025-aftermeet.mdb", "tmp/sample_data_champs_2025-aftermeet.mdb"]
    mdb_path = next((p for p in potential_mdbs if os.path.exists(p)), None)
    if not mdb_path:
        pytest.skip("Test MDB not found")

    def upload_gen():
        yield pb2.UploadDatasetRequest(filename="e2e_sync_test.mdb")
        with open(mdb_path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                yield pb2.UploadDatasetRequest(chunk=chunk)

    res = grpc_stub.UploadDataset(upload_gen())
    assert res.success is True

    # --- 2. Publish Data ---
    # Use a dummy frontend URL to verify encoding and dynamic routing
    test_frontend_origin = "https://e2e-test.mmtools.app"
    pub_res = grpc_stub.PublishMeetData(pb2.PublishMeetDataRequest(frontend_url=test_frontend_origin))
    assert pub_res.success is True

    # Verify encoding: parameters should be quoted
    # Example: base?program_url=https%3A%2F%2F...&sync_url=https%3A%2F%2F...
    assert "%3A%2F%2F" in pub_res.judge_app_url
    assert "token=" in pub_res.judge_app_url
    assert "uid=" in pub_res.judge_app_url

    # Extract sync_url
    parsed = urllib.parse.urlparse(pub_res.judge_app_url)
    params = urllib.parse.parse_qs(parsed.query)
    sync_url = params.get("sync_url", [None])[0]

    assert sync_url.startswith(test_frontend_origin)
    # --- 3. Submit DQ ---
    # We must use the REAL frontend target for the POST request
    real_submit_url = sync_url.replace(test_frontend_origin, WEB_TARGET).replace("/api/sync-dqs", "/api/submit-dq")

    # We need a real athlete and event from the meet.
    # From sample data: Event 1, Athlete 11969
    payload = {
        "clientDqId": f"e2e-dq-{int(time.time())}",
        "event": 1,
        "heat": 1,
        "lane": 1,
        "swimmer": 11969,  # Real Ath_no from sample
        "infraction_code": "1A",
    }

    resp = requests.post(real_submit_url, json=payload, timeout=15)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # --- 4. Verify MDB Persistence ---
    # Give the backend a moment to process the gRPC call triggered by the web-client
    time.sleep(2)

    # Query entries for Event 1
    entries_res = grpc_stub.GetEntries(pb2.GetEntriesRequest(event_id="1"))

    # Find our athlete
    target_entry = next((e for e in entries_res.entries if e.athlete_id == 11969), None)
    assert target_entry is not None, "Could not find entry for athlete 11969 in Event 1"

    # VERIFY DQ STATUS
    assert target_entry.status == "DQ", f"Expected status DQ, got {target_entry.status}"
