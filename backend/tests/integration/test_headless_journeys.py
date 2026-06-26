import os
import time

import grpc
import pytest
import requests

from meetmanager.v1 import meet_manager_pb2 as pb2
from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc

# Skip all tests in this module if not in CI
pytestmark = pytest.mark.skipif(
    not os.environ.get("CI"), reason="Integration tests require live services; skipping locally."
)

# Configuration for tests
# When running inside Docker, backend is '127.0.0.1:8080' (internal)
# When running from host, backend is 'localhost:8081' (or whatever BACKEND_PORT is set to)
# Next.js API is 'localhost:3000' (mapped) or 'frontend:3000' (internal)

GRPC_PORT = os.getenv("BACKEND_PORT", "8081")
GRPC_TARGET = os.getenv("TEST_GRPC_TARGET", f"127.0.0.1:{8080 if os.path.exists('/.dockerenv') else GRPC_PORT}")
WEB_TARGET = os.getenv("TEST_WEB_TARGET", f"http://{'frontend' if os.path.exists('/.dockerenv') else 'localhost'}:3000")


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
    potential_mdbs = ["/app/tmp/sample_data_champs_2025-aftermeet.mdb", "tmp/sample_data_champs_2025-aftermeet.mdb"]
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
    program_url = params.get("program_url", [None])[0]
    sync_url = params.get("sync_url", [None])[0]

    # Adjust URLs for internal network or alternative ports based on WEB_TARGET
    if "localhost:3000" in program_url:
        web_netloc = urllib.parse.urlparse(WEB_TARGET).netloc
        program_url = program_url.replace("localhost:3000", web_netloc)
    if "localhost:3000" in sync_url:
        web_netloc = urllib.parse.urlparse(WEB_TARGET).netloc
        sync_url = sync_url.replace("localhost:3000", web_netloc)

    # 2. Fetch Program Data (Headless)
    # This simulates the mobile app fetching the meet definition
    resp = requests.get(program_url, timeout=10)
    assert resp.status_code == 200
    prog_data = resp.json()
    assert "events" in prog_data
    if len(prog_data["events"]) == 0:
        pytest.skip("No events found in published data. Skipping remaining journey.")

    assert len(prog_data["events"]) > 0

    # 3. Sync DQs (Headless)
    # This simulates the mobile app pushing recorded DQs
    test_dqs = [
        {"id": int(time.time()), "swimmer_id": 1, "event_id": 1, "dq_code": "1A", "notes": "Automated Headless Test"}
    ]
    resp = requests.post(sync_url, json=test_dqs, timeout=10)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_judge_submit_single_dq(grpc_stub):
    """
    User Journey: Judge App submits a single DQ using the new stateless endpoint.
    """
    # 1. Publish Data to get urls
    pub_res = grpc_stub.PublishMeetData(pb2.PublishMeetDataRequest())
    assert pub_res.success is True

    # Extract sync_url and derive submit-dq url
    import urllib.parse

    parsed = urllib.parse.urlparse(pub_res.judge_app_url)
    params = urllib.parse.parse_qs(parsed.query)
    sync_url = params.get("sync_url", [None])[0]

    # Derive submit-dq URL from sync-dqs URL
    submit_url = sync_url.replace("/api/sync-dqs", "/api/submit-dq")

    if "localhost:3000" in submit_url:
        web_netloc = urllib.parse.urlparse(WEB_TARGET).netloc
        submit_url = submit_url.replace("localhost:3000", web_netloc)

    # 2. Submit DQ
    payload = {
        "clientDqId": f"test-dq-{int(time.time())}",
        "event": 1,
        "heat": 1,
        "lane": 1,
        "swimmer": "Test Swimmer",
        "infraction_code": "1A",
    }
    resp = requests.post(submit_url, json=payload, timeout=10)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_zip_upload_and_extraction(grpc_stub):
    """
    Test uploading a ZIP file containing an MDB dataset.
    """
    import io
    import zipfile

    # Save the original active dataset to restore later
    datasets_res = grpc_stub.ListDatasets(pb2.ListDatasetsRequest())
    prev_active = next((d.filename for d in datasets_res.datasets if d.is_active), None)

    # Create a dummy MDB content
    dummy_mdb_content = b"Fake MDB database content"
    mdb_filename = "nested/dir/zip_test_dataset.mdb"

    # Create a zip in memory containing the dummy MDB file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr(mdb_filename, dummy_mdb_content)
    zip_buffer.seek(0)
    zip_data = zip_buffer.getvalue()

    def upload_gen():
        # First chunk: filename
        yield pb2.UploadDatasetRequest(filename="Swmm7Bkup.zip")

        # Next chunks: chunk content
        chunk_size = 1024 * 1024
        for offset in range(0, len(zip_data), chunk_size):
            yield pb2.UploadDatasetRequest(chunk=zip_data[offset : offset + chunk_size])

    try:
        # Upload the ZIP file
        res = grpc_stub.UploadDataset(upload_gen())
        assert res.success is True
        assert "zip_test_dataset.mdb" in res.message or "Saved" in res.message

        # List datasets to verify that the MDB file (not the ZIP) is present and active
        datasets_res = grpc_stub.ListDatasets(pb2.ListDatasetsRequest())
        uploaded_datasets = [d.filename for d in datasets_res.datasets]
        assert "zip_test_dataset.mdb" in uploaded_datasets

        # Verify the active dataset is zip_test_dataset.mdb
        active_dataset = next((d for d in datasets_res.datasets if d.is_active), None)
        assert active_dataset is not None
        assert active_dataset.filename == "zip_test_dataset.mdb"
    finally:
        # Clean up the dataset
        try:
            grpc_stub.ClearDataset(pb2.ClearDatasetRequest(filename="zip_test_dataset.mdb"))
        except Exception:
            pass

        # Restore the original active dataset
        if prev_active and prev_active != "zip_test_dataset.mdb":
            try:
                grpc_stub.SetActiveDataset(pb2.SetActiveDatasetRequest(filename=prev_active))
            except Exception:
                pass
