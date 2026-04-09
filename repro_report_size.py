import json
import os
import sys

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

def test_lane_timer_sheets_size():
    # Load sample data
    sample_path = "backend/data/Sample_Data.json"
    with open(sample_path, "r") as f:
        cache = json.load(f)
    
    # Convert
    converter = MmToJsonConverter(table_data=cache)
    full_data = converter.convert()
    
    # Extract for Lane Timer Sheets (Type 8)
    extractor = ReportDataExtractor(converter, full_data)
    # 8 is Timer Sheets
    extracted_data = extractor.extract(8)
    
    # Generate using WeasyRenderer directly
    renderer = WeasyRenderer()
    # Type 8, Title "Timer Sheets"
    result = renderer.render(8, "Timer Sheets", extracted_data)
    
    if result["success"]:
        content = result["content"]
        size_kb = len(content) / 1024
        print(f"SUCCESS: Generated Timer Sheets. Size: {size_kb:.2f} KB")
        
        # Save locally for manual inspection if needed
        output_path = "local_timer_sheets.pdf"
        with open(output_path, "wb") as f:
            f.write(content)
        print(f"Saved to {output_path}")
        
        if size_kb < 100:
            print("WARNING: File size is < 100KB. This might be small for a multi-page report.")
        else:
            print("INFO: File size is > 100KB.")
            
        if content.startswith(b"%PDF"):
            print("INFO: Valid PDF header found.")
        else:
            print("ERROR: Invalid PDF header.")
    else:
        print(f"FAILED: {result.get('error')}")

if __name__ == "__main__":
    test_lane_timer_sheets_size()
