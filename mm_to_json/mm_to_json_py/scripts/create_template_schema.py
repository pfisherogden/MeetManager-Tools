import json
import sys


def strip_rows(input_path, output_path):
    print(f"Reading {input_path}...")
    with open(input_path, "r") as f:
        data = json.load(f)

    tables = data["tables"]

    # Tables to CLEAR (Transactional)
    CLEAR_TABLES = {
        "ATHLETE",
        "AthInfo",
        "ATHRECR",
        "CONTACT",
        "ENTRY",
        "RELAY",
        "ROSTER",  # Roster if exists
        "RESULT",
        "SPLITS",
        "ESPLITS",
        "MEET",
        "SESSIONS",
        "MTEVENT",
        "MTEVENTE",  # Events
        "TEAM",
        "COACHES",
        "JOURNAL",
        "MEMSETS",  # Workouts?
        "PREENTER",
        "DELETEENTRY",
    }

    for table_name, table_def in tables.items():
        # Only clear if in list
        # Case insensitive match
        if table_name.upper() in CLEAR_TABLES:
            print(f"Clearing rows in {table_name}")
            table_def["rows"] = []
        else:
            print(f"Keeping {len(table_def.get('rows', []))} rows in {table_name}")

    print(f"Writing empty schema to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python strip_rows.py <input.json> <output.json>")
        sys.exit(1)

    strip_rows(sys.argv[1], sys.argv[2])
