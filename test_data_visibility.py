import grpc
import sys
import os

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), 'backend/src'))

from meetmanager.v1 import meet_manager_pb2 as pb2
from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc

def test_data():
    channel = grpc.insecure_channel('127.0.0.1:50051')
    stub = pb2_grpc.MeetManagerServiceStub(channel)
    
    # 1. Ensure active dataset is the champs one
    stub.SetActiveDataset(pb2.SetActiveDatasetRequest(filename='sample_data_champs_2025-aftermeet.mdb'))
    
    # 2. Check Meets
    print("--- MEETS ---")
    resp_meets = stub.GetMeets(pb2.GetMeetsRequest())
    for m in resp_meets.meets:
        print(f"Meet: ID={m.id}, Name='{m.name}', Location='{m.location}'")
        if 'unknown' in m.name.lower():
            print("BUG 2 REPRODUCED: Meet name is unknown")
            
    # 3. Check Teams
    print("\n--- TEAMS ---")
    resp_teams = stub.GetTeams(pb2.GetTeamsRequest())
    print(f"Total Teams: {len(resp_teams.teams)}")
    if len(resp_teams.teams) == 0:
        print("BUG 3 REPRODUCED: No teams found")
    for t in resp_teams.teams[:5]:
        print(f"Team: ID={t.id}, Name='{t.name}', Athletes={t.athlete_count}")

    # 4. Check Athletes
    print("\n--- ATHLETES ---")
    resp_aths = stub.GetAthletes(pb2.GetAthletesRequest())
    print(f"Total Athletes: {len(resp_aths.athletes)}")
    if len(resp_aths.athletes) == 0:
        print("BUG 4 REPRODUCED: No athletes found")
    for a in resp_aths.athletes[:5]:
        print(f"Athlete: ID={a.id}, Name='{a.first_name} {a.last_name}', DOB='{a.date_of_birth}'")

    # 5. Check Entries (Rounding)
    print("\n--- ENTRIES (Rounding) ---")
    resp_entries = stub.GetEntries(pb2.GetEntriesRequest())
    found_long = False
    for e in resp_entries.entries[:20]:
        # Check seedTime or finalTime for long decimals
        if '.' in e.seed_time:
            parts = e.seed_time.split('.')
            if len(parts) > 1 and len(parts[1]) > 3:
                print(f"BUG 5 REPRODUCED: Long decimal in seed_time: {e.seed_time}")
                found_long = True
        if '.' in e.final_time:
            parts = e.final_time.split('.')
            if len(parts) > 1 and len(parts[1]) > 3:
                print(f"BUG 5 REPRODUCED: Long decimal in final_time: {e.final_time}")
                found_long = True
    if not found_long:
        print("Bug 5 seems fixed (no long decimals found in first 20 entries)")

if __name__ == "__main__":
    test_data()
