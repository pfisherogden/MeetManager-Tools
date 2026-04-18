import os
import sys
import time

import grpc

# Add backend/src to path for pb2 imports
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

try:
    from meetmanager.v1 import meet_manager_pb2 as pb2
    from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc
except ImportError:
    print("Error: Protos not found. Run 'just codegen' first.")
    sys.exit(1)


def test_async_bundle_flow():
    # Connect to local server (assumes 'just up' or similar is running)
    channel = grpc.insecure_channel("localhost:8080")
    stub = pb2_grpc.MeetManagerServiceStub(channel)

    print("--- Starting Async Bundle Test ---")

    # 1. Start generation
    request = pb2.GenerateReportBundleRequest(
        reports=[
            pb2.GenerateReportRequest(type=pb2.REPORT_TYPE_MEET_PROGRAM, title="Test Program 1"),
            pb2.GenerateReportRequest(type=pb2.REPORT_TYPE_MEET_PROGRAM, title="Test Program 2"),
        ],
        bundle_name="integration_test_bundle.zip",
    )

    metadata = [("x-user-id", "test-user")]
    response = stub.GenerateReportBundle(request, metadata=metadata)

    if not response.success or not response.job_id:
        print(f"FAILED: Initial request failed: {response.message}")
        return

    job_id = response.job_id
    print(f"SUCCESS: Job started with ID: {job_id}")

    # 2. Poll status
    completed = False
    attempts = 0
    max_attempts = 60  # 2 minutes

    while not completed and attempts < max_attempts:
        status_req = pb2.GetJobStatusRequest(job_id=job_id)
        status_res = stub.GetJobStatus(status_req, metadata=metadata)

        print(
            f"[{attempts}] Status: {pb2.JobStatus.Name(status_res.status)}, Progress: {status_res.progress * 100:.1f}%, Message: {status_res.message}"
        )

        if status_res.status == pb2.JOB_STATUS_COMPLETED:
            print(f"COMPLETED! Bundle URL: {status_res.bundle_url}")
            completed = True
        elif status_res.status == pb2.JOB_STATUS_FAILED:
            print(f"FAILED: {status_res.message}")
            break

        time.sleep(2)
        attempts += 1

    if not completed:
        print("FAILED: Job timed out")


if __name__ == "__main__":
    test_async_bundle_flow()
