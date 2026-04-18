import json
import os

sample_path = "MeetManager-Tools/backend/data/Sample_Data.json"
relay_path = "MeetManager-Tools/backend/tests/fixtures/Relay.json"
relay_names_path = "MeetManager-Tools/backend/tests/fixtures/RelayNames.json"

with open(sample_path, 'r') as f:
    sample = json.load(f)

with open(relay_path, 'r') as f:
    relays = json.load(f)

with open(relay_names_path, 'r') as f:
    relay_names = json.load(f)

# Remap to event 13 and team 3
fixed_relays = []
for r in relays:
    new_r = {k.lower(): str(v) if v is not None else "" for k, v in r.items()}
    if new_r.get("event_ptr") == "1":
        new_r["event_ptr"] = "13"
        new_r["team_no"] = "3"
        new_r["fin_heat"] = "1"
        new_r["fin_lane"] = "2"
    fixed_relays.append(new_r)

leg_athletes = {
    "1": "100",
    "2": "101",
    "3": "102",
    "4": "103"
}

fixed_relay_names = []
for rn in relay_names:
    new_rn = {k.lower(): str(v) if v is not None else "" for k, v in rn.items()}
    if new_rn.get("event_ptr") == "1":
        new_rn["event_ptr"] = "13"
        new_rn["team_no"] = "3"
        if new_rn.get("pos_no") in leg_athletes:
            new_rn["ath_no"] = leg_athletes[new_rn.get("pos_no")]
    fixed_relay_names.append(new_rn)

sample["Relay"] = fixed_relays
sample["RelayNames"] = fixed_relay_names

# Convert ALL keys in ALL events to lowercase for Schema A consistency
new_events = []
for event in sample.get("Event", []):
    new_event = {k.lower(): v for k, v in event.items()}
    if new_event.get("event_no") == 13 or new_event.get("event_ptr") == 13:
        new_event["ind_rel"] = "R"
        new_event["relay_size"] = 4
        print(f"DEBUG: Event 13 BEFORE: {new_event}")
    new_events.append(new_event)
sample["Event"] = new_events

with open(sample_path, 'w') as f:
    json.dump(sample, f, indent=4)

print("Successfully merged and remapped relay data + athletes + team into Sample_Data.json (Debug version)")
