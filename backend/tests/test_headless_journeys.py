import os
import json
import pytest
import grpc
import requests
import time
from meetmanager.v1 import meet_manager_pb2 as pb2
from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc

# Configuration for tests
# When running inside Docker, backend is 'localhost:8080' (internal)
# When running from host, backend is 'localhost:8081' (mapped)
# Next.js API is 'localhost:3000' (mapped) or 'frontend:3000' (internal)

GRPC_TARGET = os.getenv("TEST_GRPC_TARGET", "127.0.0.1:8080")
WEB_TARGET = os.getenv("TEST_WEB_TARGET", "http://frontend:3000")

@pytest.fixture(scope="module")
def grpc_stub():
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = pb2_grpc.MeetManagerServiceStub(channel)
    return stub

def test_meet_director_upload_and_stats(grpc_stub):
    """
    User Journey: Meet Director uploads an MDB and verifies dashboard stats.
    """
    # 1. Search for a test MDB (Local only, skip in CI if not found)
    # We use a path that works inside the docker container if volume is mounted
    # or a fallback if running locally.
    potential_mdbs = [
        "/app/tmp/sample_data_champs_2025-aftermeet.mdb",
        "tmp/sample_data_champs_2025-aftermeet.mdb"
    ]
    mdb_path = next((p for p in potential_mdbs if os.path.exists(p)), None)
    
    if not mdb_path:
        pytest.skip("Test MDB not found. Skipping ingestion journey.")

    def upload_gen():
        yield pb2.UploadDatasetRequest(filename="journey_test.mdb")
        with open(mdb_path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                yield pb2.UploadDatasetRequest(chunk=chunk)
    
    # Upload
    res = grpc_stub.UploadDataset(upload_gen())
    assert res.success is True
    
    # Verify Stats
    stats = grpc_stub.GetDashboardStats(pb2.GetDashboardStatsRequest())
    assert stats.meet_count > 0
    assert stats.athlete_count > 0

def test_judge_publish_fetch_sync(grpc_stub):
    """
    User Journey: Judge App initialization and DQ synchronization.
    """
    # 1. Publish Data
    pub_res = grpc_stub.PublishMeetData(pb2.PublishMeetDataRequest())
    assert pub_res.success is True
    assert "program_url=" in pub_res.judge_app_url
    assert "sync_url=" in pub_res.judge_app_url
    
    # Extract URLs
    import urllib.parse
    parsed = urllib.parse.urlparse(pub_res.judge_app_url)
    params = urllib.parse.parse_qs(parsed.query)
    program_url = params.get('program_url', [None])[0]
    sync_url = params.get('sync_url', [None])[0]
    
    # Adjust URLs for internal network if running inside Docker
    # The backend returns 'localhost:3000' usually, but in Docker we need 'frontend:3000'
    if "localhost:3000" in program_url and "frontend" in WEB_TARGET:
        program_url = program_url.replace("localhost:3000", "frontend:3000")
    if "localhost:3000" in sync_url and "frontend" in WEB_TARGET:
        sync_url = sync_url.replace("localhost:3000", "frontend:3000")

    # 2. Fetch Program Data (Headless)
    # This simulates the mobile app fetching the meet definition
    resp = requests.get(program_url, timeout=10)
    assert resp.status_code == 200
    prog_data = resp.json()
    assert "events" in prog_data
    assert len(prog_data["events"]) > 0

    # 3. Sync DQs (Headless)
    # This simulates the mobile app pushing recorded DQs
    test_dqs = [
        {
            "id": int(time.time()), 
            "swimmer_id": 1, 
            "event_id": 1, 
            "dq_code": "1A", 
            "notes": "Automated Headless Test"
        }
    ]
    resp = requests.post(sync_url, json=test_dqs, timeout=10)
    assert resp.status_code == 200
    assert resp.json()["success"] is True
