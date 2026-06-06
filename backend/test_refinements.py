from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
import json

def test_mixed_inclusion():
    # Use a real MDB for testing
    mdb_path = "/Users/pfo/Developer/tmp/2026_meet1_final.mdb"
    converter = MmToJsonConverter(mdb_path)
    data = converter.convert()
    
    extractor = ReportDataExtractor(converter, data)
    
    # Test Girls Filter
    print("Testing Girls Filter...")
    girls_program = extractor.extract_meet_program_data(gender_filter="Girls")
    mixed_events = [g["header"] for g in girls_program["groups"] if "Mixed" in g["header"]]
    print(f"Mixed events in Girls program: {len(mixed_events)}")
    for me in mixed_events[:5]:
        print(f"  - {me}")
        
    # Test Boys Filter
    print("\nTesting Boys Filter...")
    boys_program = extractor.extract_meet_program_data(gender_filter="Boys")
    mixed_events_boys = [g["header"] for g in boys_program["groups"] if "Mixed" in g["header"]]
    print(f"Mixed events in Boys program: {len(mixed_events_boys)}")
    for me in mixed_events_boys[:5]:
        print(f"  - {me}")

    # Test Check-in extraction
    print("\nTesting Check-in Data...")
    check_in = extractor.extract_check_in_data()
    print(f"Total athletes for check-in: {len(check_in)}")
    print(f"Example: {check_in[0]}")

if __name__ == "__main__":
    test_mixed_inclusion()
