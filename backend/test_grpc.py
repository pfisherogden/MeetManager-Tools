import os
import sys
import grpc
sys.path.append(os.path.join(os.getcwd(), "src"))
from meetmanager.v1 import meet_manager_pb2 as pb2
from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc

def test():
    token = "dev-token"
    uid = "dev-user"
    
    # We will use the production backend
    host = "mmtools-backend-ckhcthqhya-uw.a.run.app:443"
    credentials = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel(host, credentials)
    stub = pb2_grpc.MeetManagerServiceStub(channel)
    
    metadata = (
        ("authorization", f"Bearer {token}"),
        ("x-user-id", uid),
    )
    
    # List Datasets
    try:
        req = pb2.ListDatasetsRequest()
        res = stub.ListDatasets(req, metadata=metadata)
        print(f"ListDatasets success: {len(res.datasets)} datasets")
        for d in res.datasets:
            print(f" - {d.filename}")
    except Exception as e:
        print(f"ListDatasets failed: {e}")

if __name__ == "__main__":
    test()
