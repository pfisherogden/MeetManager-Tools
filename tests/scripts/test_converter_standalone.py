import os
import sys
import json

# Add backend/src to path
sys.path.insert(0, os.path.abspath("backend/src"))

from mm_to_json.mm_to_json import MmToJsonConverter

fixture_path = "tests/fixtures/anonymized_meets/2024-06-22 BH @ DP Meet2-MeetMgr.json"
if not os.path.exists(fixture_path):
    print(f"Fixture not found: {fixture_path}")
    sys.exit(1)

with open(fixture_path, "r") as f:
    fixture_wrapper = json.load(f)

table_data = fixture_wrapper["data"]
converter = MmToJsonConverter(table_data=table_data)

if "Sessitem" in converter.tables:
    df = converter.tables["Sessitem"]
    print(f"DEBUG: Sessitem head:\n{df.head()}")
    print(f"DEBUG: Sessitem dtypes:\n{df.dtypes}")
else:
    print("DEBUG: Sessitem NOT in converter.tables")

print(f"DEBUG: schema_type: {converter.schema_type}")
full_data = converter.convert()

sessions = full_data.get('sessions', [])
print(f"DEBUG: Sessions count: {len(sessions)}")

total_events = 0
total_entries = 0
for sess in sessions:
    evts = sess.get('events', [])
    total_events += len(evts)
    for evt in evts:
        total_entries += len(evt.get('entries', []))

print(f"DEBUG: Total Events: {total_events}, Total Entries: {total_entries}")
