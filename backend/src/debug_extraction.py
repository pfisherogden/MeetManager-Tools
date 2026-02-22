import logging

from mm_to_json.mm_to_json import MmToJsonConverter

logging.basicConfig(level=logging.DEBUG)

sample_mdb = "/app/data/sample_data_champs_2025-aftermeet.mdb"
converter = MmToJsonConverter(sample_mdb)
data = converter.convert()

print("\n--- DONE LOADING ---\n")
print("SESSIONS:", len(data.get("sessions", [])))
if data.get("sessions"):
    print("EVENTS IN SESSION 1:", len(data["sessions"][0].get("events", [])))
