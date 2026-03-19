import os
import sys
from mm_to_json.mm_to_json import MmToJsonConverter

def debug_dates():
    mdb_path = "data/sample_data_champs_2025-aftermeet.mdb"
    if not os.path.exists(mdb_path):
        print(f"MDB not found at {mdb_path}")
        return

    converter = MmToJsonConverter(mdb_path=mdb_path)
    df = converter.tables.get("athlete")
    if df is None or df.empty:
        print("Athlete table empty")
        return

    print(f"Total athletes: {len(df)}")
    print("Columns:", df.columns.tolist())
    
    # Check birthdate columns
    cols = [c for c in df.columns if 'birth' in c or 'date' in c]
    print("Potential date columns:", cols)
    
    if not cols:
        print("No date columns found!")
        return

    for col in cols:
        unique_vals = df[col].unique()
        print(f"\nUnique values in {col} (first 5):", unique_vals[:5])
        print(f"Count of unique values in {col}: {len(unique_vals)}")

if __name__ == "__main__":
    # Add backend/src to path
    sys.path.append(os.path.join(os.getcwd(), "backend/src"))
    debug_dates()
