import json
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mm_to_json.mm_to_json import MmToJsonConverter

logging.basicConfig(level=logging.INFO)


def debug_convert():
    sample_path = "../tests/fixtures/anonymized_champs.json"
    if not os.path.exists(sample_path):
        print(f"File not found: {sample_path}")
        return

    with open(sample_path) as f:
        raw_data = json.load(f)

    converter = MmToJsonConverter(table_data=raw_data)

    print("\n--- Converter Tables ---")
    for name, df in converter.tables.items():
        print(f"Table {name}: {len(df)} rows")

    print("\n--- Conversion ---")
    full_data = converter.convert()

    sessions = full_data.get("sessions", [])
    print(f"Sessions Found: {len(sessions)}")

    for i, sess in enumerate(sessions):
        events = sess.get("events", [])
        print(f"Session {i + 1} ({sess.get('name')}): {len(events)} events")
        if i == 0 and events:
            print(f"First event in sess 1: {events[0].get('Event_no')} - {events[0].get('Event_descr')}")


if __name__ == "__main__":
    debug_convert()
