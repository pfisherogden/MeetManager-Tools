#!/usr/bin/env python3
import sys
import argparse
import os
import json
from access_parser import AccessParser

def main():
    parser = argparse.ArgumentParser(description="mm_to_json (Python POC)")
    parser.add_argument("mdb_file", help="Path to the .mdb file")
    parser.add_argument("-d", "--output-dir", default="./", help="Directory for output (json) file")
    parser.add_argument("-w", "--watch", action="store_true", help="Watch the mdb_file (Not implemented in POC)")
    
    args = parser.parse_args()

    mdb_file = args.mdb_file
    if not os.path.exists(mdb_file):
        print(f"Error: MDB file '{mdb_file}' does not exist.")
        return 1

    print(f"Opening {mdb_file} using access-parser...")
    try:
        # Note: access_parser usage might vary slightly depending on version, 
        # but basic usage is usually AccessParser(file)
        db = AccessParser(mdb_file)
        print("Successfully opened database structure!")
        
        # List tables to prove it works
        catalog = db.catalog
        print(f"Found {len(catalog)} tables.")
        for table in list(catalog.keys())[:5]:
            print(f" - {table}")
            
    except Exception as e:
        print(f"Error reading database: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
