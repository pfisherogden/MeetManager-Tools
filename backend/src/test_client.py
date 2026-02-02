import grpc
import meet_manager_pb2
import meet_manager_pb2_grpc

def run():
    print("Trying to connect to server...")
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = meet_manager_pb2_grpc.MeetManagerServiceStub(channel)
        
        print("--- Dashboard Stats ---")
        stats = stub.GetDashboardStats(meet_manager_pb2.Empty())
        print(f"Teams: {stats.team_count}")
        print(f"Athletes: {stats.athlete_count}")
        print(f"Events: {stats.event_count}")

        if stats.team_count > 0:
            print("\n--- First 3 Teams ---")
            team_res = stub.GetTeams(meet_manager_pb2.Empty())
            for t in team_res.teams[:3]:
                print(f"{t.code}: {t.name} ({t.city}, {t.state})")
        else:
            print("No teams found (did you generate the JSONs?)")

if __name__ == '__main__':
    run()
