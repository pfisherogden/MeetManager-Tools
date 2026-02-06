import sys

import pandas as pd
from access_parser import AccessParser

# Load DB
db = AccessParser(sys.argv[1])
catalog = db.catalog

print(f"# Database Schema: {sys.argv[1]}\n")

for table_name in sorted(catalog.keys()):
    print(f"## Table: {table_name}")
    try:
        # We can't easily get strict types from access_parser without parsing,
        # but we can infer from a few rows or just list columns.
        # Let's parse and check dtypes of the dataframe.
        # Check if table exists in parse_table
        # (case insensitive usually handled by library but let's be safe)

        rows = db.parse_table(table_name)
        if isinstance(rows, dict):
            # sanitize
            max_len = 0
            for k, v in rows.items():
                if isinstance(v, list):
                    max_len = max(max_len, len(v))
            for k, v in rows.items():
                if isinstance(v, list) and len(v) < max_len:
                    rows[k] = v + [None] * (max_len - len(v))
            df = pd.DataFrame(rows)
        elif isinstance(rows, list) and rows:
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame()

        if not df.empty:
            print("| Column | Type | Example |")
            print("|---|---|---|")
            for col in df.columns:
                # Get type
                dtype = df[col].dtype
                # Get example
                example = df[col].iloc[0] if len(df) > 0 else "N/A"
                print(f"| {col} | {dtype} | {str(example)[:50]} |")
        else:
            print("(Empty Table or No Columns)")

        print("\n")
    except Exception as e:
        print(f"Error reading table: {e}\n")
