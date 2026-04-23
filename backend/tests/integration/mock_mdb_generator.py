import random
from typing import Any


def generate_mock_mdb(seed: int = 42) -> dict[str, list[dict[str, Any]]]:
    """Generates a randomized but structured MDB-like dictionary for testing."""
    random.seed(seed)

    # Meet Table
    meet = [
        {
            "Meet_name1": f"Meet {random.randint(100, 999)}",
            "Meet_start": "2024-06-01",
            "Meet_location": "Test Pool",
            "Meet_numlanes": 6,
            "Calc_date": "2024-06-01",
        }
    ]

    # Teams
    teams = [
        {"TCode": "DP", "TName": "Del Prado Stingrays"},
        {"TCode": "FAST", "TName": "FAST Dolphins"},
        {"TCode": "SHRK", "TName": "Meadows Sharks"},
    ]

    # Sessions
    sessions = [
        {"SESSION": 1, "SessName": "Morning", "Day": 1, "StartTime": 480},
        {"SESSION": 2, "SessName": "Afternoon", "Day": 1, "StartTime": 780},
    ]

    # Events
    events = []
    sessitems = []
    for i in range(1, 11):
        e_ptr = i
        events.append({"Event_no": i, "Event_ptr": e_ptr, "Ind_rel": "I" if i % 2 == 0 else "R"})
        sessitems.append({"Sess_ptr": 1 if i <= 5 else 2, "Event_ptr": e_ptr, "Sess_order": i})

    # Athletes & Entries
    athletes = []
    entries = []
    for i in range(1, 21):
        a_ptr = i
        athletes.append(
            {"Athlete": a_ptr, "First": f"First{i}", "Last": f"Last{i}", "TCode": random.choice(["DP", "FAST", "SHRK"])}
        )
        entries.append({"Entry": i, "Athlete": a_ptr, "MtEvent": random.randint(1, 10)})

    return {
        "Meet": meet,
        "Team": teams,
        "Session": sessions,
        "Sessitem": sessitems,
        "Event": events,
        "athlete": athletes,
        "Entry": entries,
        "Scoring": [{"Ind1": 9, "Rel1": 12}],
    }
