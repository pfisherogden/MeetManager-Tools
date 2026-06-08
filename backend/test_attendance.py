import logging
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def test_attendance_participation():
    mdb_path = "/Users/pfo/Developer/tmp/2026_meet1_final.mdb"
    converter = MmToJsonConverter(mdb_path)
    data = converter.convert()
    
    extractor = ReportDataExtractor(converter, data)
    
    print("Testing Attendance Participation Data...")
    check_in_data = extractor.extract_check_in_data(team_filter="DP")
    
    # Check for someone we know is in a relay or multiple events
    # Example: search for 'Prater'
    praters = [a for a in check_in_data if "Prater" in a["Last Name"]]
    for p in praters:
        print(f"Swimmer: {p['Preferred Name']} {p['Last Name']}")
        print(f"  Strokes: Free={p['Free']}, Fly={p['Fly']}, Back={p['Back']}, Breast={p['Breast']}, IM={p['IM']}")
        print(f"  Relays: Free={p['Free Relay']}, Medley={p['Medley Relay']}")

    # Total check
    print(f"\nTotal athletes: {len(check_in_data)}")
    has_relay = [a for a in check_in_data if a["Free Relay"] == "X" or a["Medley Relay"] == "X"]
    print(f"Athletes in relays: {len(has_relay)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_attendance_participation()
