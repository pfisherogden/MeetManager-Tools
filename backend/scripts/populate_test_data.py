import sys
import os
import random
from typing import List

# Add backend/src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from mm_to_json.mdb_writer import open_db, add_athlete, add_entry, add_relay_team

# Team Abbr -> ID
TEAM_IDS = {"DP": 1, "FAST": 2}

AGE_GROUPS = [
    (0, 6, "6&U"),
    (7, 8, "7-8"),
    (9, 10, "9-10"),
    (11, 12, "11-12"),
    (13, 14, "13-14"),
    (15, 18, "15-18")
]

def populate(mdb_path: str):
    print(f"Populating {mdb_path} with synthetic data...")
    db = open_db(mdb_path)
    
    try:
        # Get Meet ID (assuming 1)
        meet_id = 1
        
        # 1. Add Athletes
        ath_id = 1
        ath_by_group = {"DP": {}, "FAST": {}}
        
        for team in ["DP", "FAST"]:
            team_id = TEAM_IDS[team]
            for low, high, name in AGE_GROUPS:
                ath_by_group[team][name] = {"F": [], "M": []}
                for i in range(5):
                    # Girls
                    first = f"{team}G{name.replace('&','')}_{i}"
                    last = "Swimmer"
                    add_athlete(db, ath_id, team_id, first, last, "F", random.randint(low, high))
                    ath_by_group[team][name]["F"].append(ath_id)
                    ath_id += 1
                    
                    # Boys
                    first = f"{team}B{name.replace('&','')}_{i}"
                    last = "Swimmer"
                    add_athlete(db, ath_id, team_id, first, last, "M", random.randint(low, high))
                    ath_by_group[team][name]["M"].append(ath_id)
                    ath_id += 1
        
        print(f"  Added {ath_id-1} athletes.")
        
        # 2. Add Entries
        # Load events
        event_table = db.getTable("Event")
        if not event_table:
            event_table = db.getTable("MTEVENT")
        
        events = []
        for row in event_table:
            events.append({
                "MtEvent": row.get("MtEvent"),
                "MtEv": row.get("MtEv"),
                "Sex": row.get("Event_sex"),
                "I_R": row.get("Ind_rel"),
                "Low": row.get("Low_age"),
                "High": row.get("High_Age"),
                "Dist": row.get("Event_dist"),
                "Stroke": row.get("Event_stroke")
            })
        
        entry_id = 1
        relay_id = 1
        
        for evt in events:
            # Match by age range
            low, high = evt["Low"], evt["High"]
            gender = evt["Sex"] # G, B, X
            is_relay = (evt["I_R"] == "R")
            
            # Find group name for athletes
            group_name = None
            for glow, ghigh, gname in AGE_GROUPS:
                if glow == low and ghigh == high:
                    group_name = gname
                    break
            
            if not group_name: continue

            # Map gender filter to F/M
            genders = ["F"] if gender == "G" else (["M"] if gender == "B" else ["F", "M"])
            
            for g in genders:
                # Add DP entries (Even lanes: 2, 4, 6)
                if group_name in ath_by_group["DP"]:
                    athletes = ath_by_group["DP"][group_name][g]
                    if is_relay:
                        # Add one DP relay
                        add_relay_team(db, relay_id, meet_id, TEAM_IDS["DP"], "A", g, athletes=athletes[:4])
                        relay_id += 1
                    else:
                        # Add DP individuals
                        for i, aid in enumerate(athletes[:3]):
                            lane = (i + 1) * 2
                            add_entry(db, entry_id, aid, evt["MtEvent"], TEAM_IDS["DP"], 1, lane, meet_id)
                            entry_id += 1
                
                # Add FAST entries (Odd lanes: 1, 3, 5)
                if group_name in ath_by_group["FAST"]:
                    athletes = ath_by_group["FAST"][group_name][g]
                    if not is_relay:
                        for i, aid in enumerate(athletes[:3]):
                            lane = i * 2 + 1
                            if lane > 6: continue
                            add_entry(db, entry_id, aid, evt["MtEvent"], TEAM_IDS["FAST"], 1, lane, meet_id)
                            entry_id += 1
        
        print(f"  Added {entry_id-1} entries.")

    finally:
        db.close()
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python populate_test_data.py <mdb_path>")
    else:
        populate(sys.argv[1])
