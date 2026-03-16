import grpc
import sys
import os

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), 'backend/src'))

from meetmanager.v1 import meet_manager_pb2 as pb2
from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc

def test_bundle():
    channel = grpc.insecure_channel('127.0.0.1:50051')
    stub = pb2_grpc.MeetManagerServiceStub(channel)
    
    # 1. Ensure active dataset is the champs one
    stub.SetActiveDataset(pb2.SetActiveDatasetRequest(filename='sample_data_champs_2025-aftermeet.mdb'))
    
    # 2. Try to generate a bundle
    request = pb2.GenerateReportBundleRequest(
        bundle_name="test_bundle.zip",
        reports=[
            pb2.GenerateReportRequest(type=pb2.REPORT_TYPE_MEET_PROGRAM, title="Test Program"),
            pb2.GenerateReportRequest(type=pb2.REPORT_TYPE_LINEUPS, title="Test Lineups"),
        ]
    )
    
    try:
        response = stub.GenerateReportBundle(request)
        print(f"Success: {response.success}")
        print(f"Message: {response.message}")
        if response.success:
            print(f"Zip size: {len(response.zip_content)} bytes")
            with open("repro_bundle.zip", "wb") as f:
                f.write(response.zip_content)
    except Exception as e:
        print(f"gRPC Error: {e}")

if __name__ == "__main__":
    test_bundle()
