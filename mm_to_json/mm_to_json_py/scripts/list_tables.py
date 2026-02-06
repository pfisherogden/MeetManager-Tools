import os
import sys

from access_parser import AccessParser


def list_tables(mdb_path):
    if not os.path.exists(mdb_path):
        print(f"File not found: {mdb_path}")
        return

    try:
        db = AccessParser(mdb_path)
        print("Tables found:")
        for table in db.catalog:
            print(f"- {table}")

        if "CUSTOMRPTS" in db.catalog:
            print("\nCUSTOMRPTS table DOES exist.")
        else:
            print("\nCUSTOMRPTS table DOES NOT exist.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python list_tables.py <mdb_file>")
    else:
        list_tables(sys.argv[1])
