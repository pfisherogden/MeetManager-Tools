import os
import sys
import subprocess
import csv
import io

# Add backend/src to path
sys.path.append(os.path.dirname(__file__))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

def load_mdb(db_path):
    print(f"Exporting tables from {db_path} using mdb-export...")
    try:
        tables = subprocess.check_output(["mdb-tables", "-1", db_path]).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error listing tables: {e}")
        return {}

    data = {}
    for t in tables:
        if not t.strip():
            continue
        try:
            csv_out = subprocess.check_output(["mdb-export", db_path, t]).decode("utf-8")
            data[t] = list(csv.DictReader(io.StringIO(csv_out)))
        except Exception as e:
            print(f"Skipping table {t}: {e}")
    return data

def main():
    # 1. Setup paths
    data_path = "../tmp/sample_data_champs_2025-aftermeet.mdb"
    if not os.path.exists(data_path):
        data_path = "tmp/sample_data_champs_2025-aftermeet.mdb"
        
    output_dir = "../tmp/generated_weasyprint_reports"
    os.makedirs(output_dir, exist_ok=True)
    output_pdf = os.path.join(output_dir, "Meet_Program_Test.pdf")
    
    # 2. Load Data
    print(f"Loading MDB from {data_path}...")
    table_data = load_mdb(data_path)
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    # 3. Extract Data
    print("Extracting Meet Program data...")
    program_data = extractor.extract_meet_program_data()
    
    # 4. Render with WeasyPrint
    print(f"Rendering PDF to {output_pdf}...")
    renderer = WeasyRenderer(output_pdf)
    renderer.render_meet_program(program_data)
    
    print(f"Success! Report generated at {output_pdf}")

if __name__ == "__main__":
    main()
