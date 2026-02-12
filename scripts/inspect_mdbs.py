import sys
import os
import pandas as pd
import jpype
import jpype.imports
from datetime import datetime

# Add backend/src to path for mm_to_json imports
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter

def inspect_mdb(mdb_path):
    print(f"\n{'='*50}")
    print(f"Inspecting: {os.path.basename(mdb_path)}")
    print(f"{'='*50}")
    
    if not os.path.exists(mdb_path):
        print(f"Error: File not found: {mdb_path}")
        return

    try:
        # Initialize converter
        # This will trigger mdb_writer.ensure_jvm_started()
        converter = MmToJsonConverter(mdb_path=mdb_path)
        
        print(f"Schema Type Detected: {converter.schema_type}")
        print("\nTables and Row Counts:")
        for logical, df in converter.tables.items():
            if df is not None:
                print(f"  - {logical:12}: {len(df):5} rows")
            else:
                print(f"  - {logical:12}: EMPTY/NOT FOUND")
                
        # List actual physical tables from the DB
        if converter.db:
            print("\nPhysical Tables in Database:")
            all_tables = [str(t) for t in converter.db.getTableNames()]
            for t in sorted(all_tables):
                print(f"  - {t}")
        
    except Exception as e:
        print(f"Error during inspection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    targets = [
        "tmp/2024-06-22 BH @ DP Meet2-MeetMgr.mdb",
        "tmp/sample_data_champs_2025-aftermeet.mdb"
    ]
    
    for t in targets:
        full_path = os.path.join(os.getcwd(), t)
        inspect_mdb(full_path)
