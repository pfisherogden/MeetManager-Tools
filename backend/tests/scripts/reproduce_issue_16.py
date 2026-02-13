import os
import sys

import grpc

# Add backend/src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from meetmanager.v1 import meet_manager_pb2, meet_manager_pb2_grpc


def run():
    print("Connecting to gRPC server...")
    channel = grpc.insecure_channel("localhost:50051")
    stub = meet_manager_pb2_grpc.MeetManagerServiceStub(channel)

    print("Calling ListDatasets...")
    try:
        response = stub.ListDatasets(meet_manager_pb2.ListDatasetsRequest())
        mdb_file = None
        for d in response.datasets:
            print(f" - {d.filename} (active={d.is_active})")
            if d.filename.endswith(".mdb") and "after meet" in d.filename:
                mdb_file = d.filename

        if mdb_file:
            print(f"Switching to {mdb_file}...")
            stub.SetActiveDataset(meet_manager_pb2.SetActiveDatasetRequest(filename=mdb_file))
            print("Dataset switched.")

            # Debug MDB directly
            import subprocess

            print("\n--- Direct MDB Inspection ---")
            mdb_path = os.path.join("/app/data", mdb_file)
            try:
                tables = subprocess.check_output(["mdb-tables", "-1", mdb_path]).decode().split()
                print(f"Tables in MDB: {tables}")

                if "Relay" in tables or "RELAY" in tables:
                    t_name = "Relay" if "Relay" in tables else "RELAY"
                    print(f"Dumping first 5 rows of {t_name}...")
                    rows = subprocess.check_output(["mdb-export", mdb_path, t_name]).decode().splitlines()
                    print(f"Total rows: {len(rows) - 1}")  # -1 for header
                    for r in rows[:6]:
                        print(r)
                else:
                    print("Relay table not found in MDB.")

                if "RelayNames" in tables:
                    print("Dumping first 5 rows of RelayNames...")
                    rows = subprocess.check_output(["mdb-export", mdb_path, "RelayNames"]).decode().splitlines()
                    print(f"Total rows: {len(rows) - 1}")
                    for r in rows[:6]:
                        print(r)
                else:
                    print("RelayNames table not found in MDB.")

            except Exception as e:
                print(f"Error inspecting MDB: {e}")
            print("-----------------------------\n")

        print("Calling GetRelays...")
        response = stub.GetRelays(meet_manager_pb2.GetRelaysRequest())
        print(f"GetRelays returned {len(response.relays)} relays.")
        if len(response.relays) > 0:
            print("Sample Relay:", response.relays[0])
        else:
            print("No relays found.")

    except grpc.RpcError as e:
        print(f"RPC Error: {e}")


if __name__ == "__main__":
    run()
