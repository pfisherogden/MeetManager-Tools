import sys
import os
import json
import pdfplumber

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "../src"))
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def dump_pdf(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        return text

def test_report(mdb_path, team, gender, age):
    conv = MmToJsonConverter(mdb_path)
    extractor = ReportDataExtractor(conv)
    return extractor.extract_meet_program_data(team_filter=team, gender_filter=gender, age_group_filter=age)

if __name__ == "__main__":
    mdb = "/Users/pfo/Developer/tmp/2026-05-30_DP_at_FAST_actual.mdb"
    
    # 1. Girls 9-10 Lineup
    data = test_report(mdb, "DP", "Girls", "9-10")
    print("--- Girls 9-10 Lineup (MMTools) ---")
    for group in data["groups"]:
        print(f"Header: {group['header']}")
        for heat in group.get("heats", []):
            print(f"  {heat['header']}")
            for item in heat["sub_items"]:
                if item.get("is_relay"):
                    print(f"    L{item['lane']}: {item['name']} ({', '.join(item['swimmers'])})")
                else:
                    print(f"    L{item['lane']}: {item['name']}")

    text = dump_pdf("/Users/pfo/Developer/tmp/girls_9-10_line_up.pdf")
    print("\n--- Reference PDF ---")
    print("\n".join(text.split("\n")[:20]))

    # 2. Boys 9-10 Lineup
    data = test_report(mdb, "DP", "Boys", "9-10")
    print("\n--- Boys 9-10 Lineup (MMTools) ---")
    for group in data["groups"]:
        print(f"Header: {group['header']}")
        for heat in group.get("heats", []):
            print(f"  {heat['header']}")
            for item in heat["sub_items"]:
                if item.get("is_relay"):
                    print(f"    L{item['lane']}: {item['name']} ({', '.join(item['swimmers'])})")
                else:
                    print(f"    L{item['lane']}: {item['name']}")

    text = dump_pdf("/Users/pfo/Developer/tmp/boys_9-10_line_up.pdf")
    print("\n--- Reference PDF ---")
    print("\n".join(text.split("\n")[:20]))
