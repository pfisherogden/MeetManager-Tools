import sys
import os
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "../src"))
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

if __name__ == "__main__":
    mdb = "/Users/pfo/Developer/tmp/2026-05-30_DP_at_FAST_actual.mdb"
    conv = MmToJsonConverter(mdb)
    full_data = conv.convert()
    for s in full_data["sessions"]:
        for e in s["events"]:
            if e["eventNum"] == 6:
                for entry in e["entries"]:
                    print(entry["relayAthletes"])
