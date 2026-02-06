import json
import os
import shutil
import subprocess
import sys

# Add src to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from mm_to_json import mdb_writer

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Singers23.mdb is in the root of the repo (mm_to_json/)
# ../.. relative to tests/
MDB_SOURCE = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "Singers23.mdb")
MDB_TEST = os.path.join(BASE_DIR, "Test_Write.mdb")
CONVERTER_SCRIPT = os.path.abspath(os.path.join(BASE_DIR, "../src/mm_to_json/mm_to_json.py"))


def setup_fresh_db():
    if os.path.exists(MDB_TEST):
        os.remove(MDB_TEST)
    shutil.copy(MDB_SOURCE, MDB_TEST)
    print(f"Created fresh test DB at {MDB_TEST}")


def populate_test_data():
    print("Populating DB with test entities...")
    db = mdb_writer.open_db(MDB_TEST)
    try:
        # 1. Add Session
        # Session 1 is typically morning, let's add Session 5 (Evening)
        print("- Adding Session 5")
        mdb_writer.add_session(db, session_num=5, day=1, start_time="05:00", meet_id=3, am_pm=True)

        # 2. Add Team
        # ID 9999 (Proposed)
        print("- Adding Team TEST-US")
        real_team_id = mdb_writer.add_team(
            db, team_id=9999, abbr="TEST", name="Test Team", lsc="US"
        )
        print(f"  Team Added: {real_team_id}")

        # 3. Add Athlete
        # ID 8888 (Proposed)
        print("- Adding Athlete John Doe")
        real_ath_id = mdb_writer.add_athlete(
            db,
            athlete_id=8888,
            team_id=real_team_id,
            first="John",
            last="Doe",
            gender="M",
            age=16,
            school_year="JR",
        )
        print(f"  Athlete Added: {real_ath_id}")

        # 4. Add Event
        # ID 101 (Proposed), Session 5, Event #101
        print("- Adding Event #101")
        real_event_id = mdb_writer.add_event(
            db,
            event_id=101,
            session_num=5,
            event_no=101,
            distance=100,
            stroke=1,
            gender="F",
            meet_id=3,
            age_low=15,
            age_high=18,
        )
        print(f"  Event Added: {real_event_id}")

        # 5. Add Entry
        # ID 6666, Athlete real_ath_id, Event real_event_id
        print("- Adding Entry for John Doe in Event #101")
        mdb_writer.add_entry(
            db,
            entry_id=6666,
            athlete_id=real_ath_id,
            event_id=real_event_id,
            team_id=real_team_id,
            heat=1,
            lane=4,
            meet_id=3,
        )

    finally:
        db.close()
    print("Population complete.")

    # Debug: Inspect Tables
    db = mdb_writer.open_db(MDB_TEST)
    try:
        print("\n--- DB INSPECTION ---")
        t_sess = db.getTable("SESSIONS")
        print(f"SESSIONS ({t_sess.getRowCount()} rows):")
        for row in t_sess:
            print(f"  ID: {row.get('SESSION')}, ME: {row.get('MEETID')}, T: {row.get('STARTTIME')}")

        t_evt = db.getTable("MTEVENT")
        print(f"MTEVENT ({t_evt.getRowCount()} rows):")
        for row in t_evt:
            # Only show new event or similar
            if row.get("MtEv") == 101 or row.get("MtEvent") == 101:
                print(
                    f"  ID: {row.get('MtEvent')}, No: {row.get('MtEv')}, "
                    f"Sess: {row.get('Session')}, Meet: {row.get('Meet')}"
                )
        print("--- END DB INSPECTION ---\n")
    finally:
        db.close()


def run_conversion():
    print("Running mm_to_json.py...")
    # Run the converter pointing to our test MDB
    # Output to current dir as Test_Write.json

    cmd = [sys.executable, CONVERTER_SCRIPT, MDB_TEST, "-d", BASE_DIR]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Conversion failed:")
        print(result.stderr)
        return None

    json_path = os.path.join(BASE_DIR, "Test_Write.json")
    if not os.path.exists(json_path):
        print("JSON output file not found.")
        return None

    print(f"Conversion success. Reading {json_path}...")
    with open(json_path, "r") as f:
        return json.load(f)


def verify_data(data):
    print("Verifying JSON data schema...")

    # 1. Verify Session
    sessions = data.get("sessions", [])
    sess_5 = next((s for s in sessions if s["sessionNum"] == 5), None)
    if not sess_5:
        print("FAIL: Session 5 not found in JSON.")
        return False
    print("PASS: Session 5 found.")

    # 2. Verify Event (should be in session 5)
    events = sess_5.get("events", [])
    # Look for event by Description part
    expected_desc = "F 15 - 18 100 Freestyle"
    found_event = next((e for e in events if expected_desc in e["eventDesc"]), None)

    if not found_event:
        print(
            f"FAIL: Event with desc '{expected_desc}' not found in Session 5. "
            f"Events found: {[e['eventDesc'] for e in events]}"
        )
        return False

    print(f"PASS: Event found: {found_event['eventDesc']} (Num: {found_event['eventNum']})")

    # 3. Verify Entry
    entries = found_event.get("entries", [])
    entry_doe = next((e for e in entries if "Doe" in e["name"]), None)
    if not entry_doe:
        print("FAIL: Entry for John Doe not found.")
        return False

    if entry_doe["team"] != "Test Team":  # or abbr depending on logic
        print(f"WARN: Team '{entry_doe['team']}' vs expected 'Test Team'")

    if entry_doe["heat"] != 1 or entry_doe["lane"] != 4:
        print(f"FAIL: Heat/Lane mismatch. Got {entry_doe['heat']}/{entry_doe['lane']}")
        return False

    print("PASS: Entry confirmed.")
    return True


def main():
    try:
        setup_fresh_db()
        populate_test_data()
        data = run_conversion()
        if data:
            if verify_data(data):
                print("\nALL TESTS PASSED")
            else:
                print("\nTESTS FAILED")
    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
