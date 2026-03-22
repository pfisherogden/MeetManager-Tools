
import os
import json
import logging
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def test_age_extraction():
    fixture_path = "tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json"
    with open(fixture_path, 'r') as f:
        data = json.load(f)
    
    table_data = data["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    # Test extract_lane_timer_sheets_data
    report_data = extractor.extract_lane_timer_sheets_data()
    
    found_any_age = False
    for group in report_data["groups"]:
        for item in group["sub_items"]:
            if not item["is_relay"]:
                print(f"Name: {item['name']}, Age: {item['age']}")
                if item["age"] and item["age"] != "0":
                    found_any_age = True
                    break
        if found_any_age: break
    
    assert found_any_age, "No ages found in extracted data!"
    print("SUCCESS: Found ages in extracted data.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        test_age_extraction()
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
