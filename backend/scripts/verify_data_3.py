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
    extractor = ReportDataExtractor(conv)
    data = extractor.extract_meet_program_data()
    for group in data["groups"]:
        if "Event 6" in group["header"]:
            for heat in group["heats"]:
                for item in heat["sub_items"]:
                    print(item["swimmers"])
