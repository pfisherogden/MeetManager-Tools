import os
import random
import sys

# Add src to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, "../src"))
sys.path.append(SRC_DIR)

from mm_to_json import mdb_restorer, mdb_writer  # noqa: E402


def generate(output_mdb, empty_schema_json):
    if os.path.exists(output_mdb):
        os.remove(output_mdb)

    print(f"Creating empty DB from {empty_schema_json}...")
    mdb_restorer.restore_db(empty_schema_json, output_mdb)

    db = mdb_writer.open_db(output_mdb)
    try:
        # Configuration
        MEET_ID = 1
        SESSION_NUM = 1

        # 1. Add Session
        print("Adding Session 1...")
        mdb_writer.add_session(db, SESSION_NUM, 1, "08:00", MEET_ID, am_pm=True)

        # 2. Add Teams
        teams = [
            {"name": "Dolphins", "abbr": "DOL", "id": 10},
            {"name": "Sharks", "abbr": "SHK", "id": 20},
        ]

        team_ids = []
        for t in teams:
            tid = mdb_writer.add_team(db, t["id"], t["abbr"], t["name"], lsc="CA")
            print(f"Added Team {t['name']} (ID: {tid})")
            team_ids.append(tid)

        # 3. Add Events (50 Events)
        # Mix of Age Groups, Genders, Strokes
        events = []
        strokes = {1: "Free", 2: "Back", 3: "Breast", 4: "Fly", 5: "IM"}
        distances = [25, 50, 100]
        ages = [
            (8, 8, "8&U"),
            (9, 10, "9-10"),
            (11, 12, "11-12"),
            (13, 14, "13-14"),
            (15, 18, "15-18"),
        ]
        genders = ["F", "M"]

        evt_num = 1

        # Generate Individual Events (40 events)
        for age in ages:
            for dist in distances:
                for stroke_id, stroke_name in strokes.items():
                    if dist == 25 and age[1] > 10:
                        continue  # Skip 25 for older

                    # Create M & F events
                    for gender in genders:
                        if len(events) >= 46:
                            break

                        mdb_writer.add_event(
                            db,
                            evt_num,
                            SESSION_NUM,
                            evt_num,
                            dist,
                            stroke_id,
                            gender,
                            MEET_ID,
                            age_low=age[0],
                            age_high=age[1],
                        )
                        events.append(
                            {
                                "id": evt_num,
                                "num": evt_num,
                                "age": age,
                                "gender": gender,
                                "relay": False,
                            }
                        )
                        evt_num += 1

        # Generate Relay Events (4 events)
        # 200 Free Relay
        for age in [(11, 12), (13, 14)]:
            for gender in genders:
                mdb_writer.add_event(
                    db,
                    evt_num,
                    SESSION_NUM,
                    evt_num,
                    200,
                    1,
                    gender,
                    MEET_ID,
                    i_r="R",
                    age_low=age[0],
                    age_high=age[1],
                )
                events.append(
                    {"id": evt_num, "num": evt_num, "age": age, "gender": gender, "relay": True}
                )
                evt_num += 1

        print(f"Added {len(events)} Events.")

        # 4. Add Athletes (20 per team)
        # Guarantee Relay Teams first:
        # Need 4 Boys 11-12, 4 Girls 11-12, 4 Boys 13-14, 4 Girls 13-14 per team to cover relays
        # That's 16 athletes. The remaining 4 can be random.

        athletes = []
        for tid in team_ids:
            # Relay Cohorts
            cohorts = [
                {"age": 11, "gender": "M", "count": 4},
                {"age": 11, "gender": "F", "count": 4},
                {"age": 13, "gender": "M", "count": 4},
                {"age": 13, "gender": "F", "count": 4},
            ]

            ath_idx = 1
            for c in cohorts:
                for _ in range(c["count"]):
                    fname = f"Relayer{ath_idx}"
                    lname = f"Team{tid}"
                    aid = mdb_writer.add_athlete(db, 0, tid, fname, lname, c["gender"], c["age"])
                    athletes.append(
                        {"id": aid, "team": tid, "age": c["age"], "gender": c["gender"]}
                    )
                    ath_idx += 1

            # Fill remaining (up to 20 total)
            remaining = 20 - len(cohorts) * 4  # Should be 4
            for i in range(remaining):
                age = random.randint(8, 18)
                gender = "F" if i % 2 == 0 else "M"
                fname = f"Athlete{i}"
                lname = f"Team{tid}"
                aid = mdb_writer.add_athlete(db, 0, tid, fname, lname, gender, age)
                athletes.append({"id": aid, "team": tid, "age": age, "gender": gender})

        print(f"Added {len(athletes)} Athletes.")

        # 5. Add Individual Entries
        entry_cnt = 0
        for ath in athletes:
            # Find eligible events
            for evt in events:
                if evt["relay"]:
                    continue
                if evt["gender"] == ath["gender"] and evt["age"][0] <= ath["age"] <= evt["age"][1]:
                    # Enter!
                    mdb_writer.add_entry(
                        db,
                        0,
                        ath["id"],
                        evt["id"],
                        ath["team"],
                        heat=1,
                        lane=random.randint(1, 6),
                        meet_id=MEET_ID,
                    )
                    entry_cnt += 1

        print(f"Added {entry_cnt} Individual Entries.")

        # 6. Add Relay Entries
        relay_cnt = 0
        for evt in events:
            if not evt["relay"]:
                continue

            # Form team for each team
            for tid in team_ids:
                # Find 4 eligible athletes
                team_aths = [
                    a
                    for a in athletes
                    if a["team"] == tid
                    and a["gender"] == evt["gender"]
                    and evt["age"][0] <= a["age"] <= evt["age"][1]
                ]

                if len(team_aths) >= 4:
                    relay_members = [a["id"] for a in team_aths[:4]]

                    # Create Relay Team
                    r_id = mdb_writer.add_relay_team(
                        db, 0, MEET_ID, tid, "A", evt["gender"], athletes=relay_members
                    )

                    # specific age range code logic skipped for simplicity, using 0 or lo_hi logic

                    # Create Entry
                    mdb_writer.add_entry(
                        db, 0, r_id, evt["id"], tid, heat=1, lane=3, meet_id=MEET_ID, i_r="R"
                    )
                    relay_cnt += 1

        print(f"Added {relay_cnt} Relay Entries.")

    finally:
        db.close()

    print("Database Generation Complete.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run generate_sample_data.py <template_schema.json> <output.mdb>")
        sys.exit(1)
    generate(sys.argv[2], sys.argv[1])
