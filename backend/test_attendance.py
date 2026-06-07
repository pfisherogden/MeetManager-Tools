import logging
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def test_attendance_team_filter():
    mdb_path = "/Users/pfo/Developer/tmp/2026_meet1_final.mdb"
    converter = MmToJsonConverter(mdb_path)
    data = converter.convert()
    
    extractor = ReportDataExtractor(converter, data)
    
    # Test DP Filter
    print("Testing DP Attendance Filter...")
    dp_data = extractor.extract_check_in_data(team_filter="DP")
    teams_dp = set(a["Team"] for a in dp_data)
    print(f"Teams in DP filter: {teams_dp}")
    print(f"Total DP athletes: {len(dp_data)}")
    
    # Test FAST Filter
    print("\nTesting FAST Attendance Filter...")
    fast_data = extractor.extract_check_in_data(team_filter="FAST")
    teams_fast = set(a["Team"] for a in fast_data)
    print(f"Teams in FAST filter: {teams_fast}")
    print(f"Total FAST athletes: {len(fast_data)}")

    # Test All Teams
    print("\nTesting All Teams Attendance Filter...")
    all_data = extractor.extract_check_in_data(team_filter="All Teams")
    teams_all = set(a["Team"] for a in all_data)
    print(f"Teams in All filter: {teams_all}")
    print(f"Total All athletes: {len(all_data)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_attendance_team_filter()
