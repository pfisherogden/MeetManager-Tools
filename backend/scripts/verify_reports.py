import sys
import os
import json
import pdfplumber

# Add paths
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "../src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

def dump_pdf(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        return text

def test_report(mdb_path, report_type, **kwargs):
    conv = MmToJsonConverter(mdb_path)
    extractor = ReportDataExtractor(conv)
    if report_type == "meet_program":
        return extractor.extract_meet_program_data(**kwargs)
    return None

if __name__ == "__main__":
    mdb = "/Users/pfo/Developer/tmp/2026-05-30_DP_at_FAST_actual.mdb"
    
    pdfs = {
        "Girls Posting": "/Users/pfo/Developer/tmp/girls_meet_program_for_posting.pdf",
        "Boys Posting": "/Users/pfo/Developer/tmp/boys_meet_program_for_posting.pdf",
        "Girls 9-10 Lineup": "/Users/pfo/Developer/tmp/girls_9-10_line_up.pdf",
        "Boys 9-10 Lineup": "/Users/pfo/Developer/tmp/boys_9-10_line_up.pdf",
    }
    
    print("--- MMTools Data Extraction ---")
    conv = MmToJsonConverter(mdb)
    extractor = ReportDataExtractor(conv)
    
    # Girls Posting
    print("\nGirls Posting Data:")
    data = extractor.extract_meet_program_data(gender_filter="Girls")
    for group in data["groups"][:3]: # print first 3 groups
        print(f"Header: {group['header']}")
        if group.get("heats"):
            for heat in group["heats"]:
                print(f"  {heat['header']}")
                for item in heat["sub_items"]:
                    print(f"    {item}")
        else:
            for item in group.get("sub_items", []):
                print(f"  {item}")

    print("\n--- Reference PDF Text (Girls Posting) ---")
    text = dump_pdf(pdfs["Girls Posting"])
    print(text[:1000])

