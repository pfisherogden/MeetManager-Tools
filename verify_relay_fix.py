import json
import os
import sys

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter

def verify_relay_json():
    # Load sample data
    sample_path = "backend/data/Sample_Data.json"
    with open(sample_path, "r") as f:
        cache = json.load(f)
    
    # Convert
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    
    # Find a relay event
    relay_events = [e for e in full_data.get("events", []) if e.get("isRelay")]
    
    if not relay_events:
        print("No relay events found in sample data.")
        return

    print(f"Found {len(relay_events)} relay events.")
    
    # Check first relay event entries
    event = relay_events[0]
    print(f"Event: {event.get('name')}")
    
    heats = event.get("heats", [])
    for heat in heats:
        for entry in heat.get("entries", []):
            if entry.get("isRelay"):
                print(f"Entry: {entry.get('name')}")
                print(f"  - relaySwimmers: {entry.get('relaySwimmers')}")
                print(f"  - members: {entry.get('members')}")
                
                if "members" in entry:
                    print("SUCCESS: 'members' key found in entry.")
                else:
                    print("FAILURE: 'members' key MISSING from entry.")
                return # Just check one

if __name__ == "__main__":
    verify_relay_json()
