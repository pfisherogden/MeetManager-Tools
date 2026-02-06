import os

import mdb_writer


def check_autonumber():
    mdb_path = "Singers23.mdb"
    # Use the test one if needed, but source is better for "Meet Manager's" definitions
    if not os.path.exists(mdb_path):
        mdb_path = "../Singers23.mdb"

    print(f"Checking schema in {mdb_path}...")
    db = mdb_writer.open_db(mdb_path)

    # Import after JVM start

    tables_to_check = {
        "MTEVENT": "MtEvent",
        "ATHLETE": "Athlete",
        "TEAM": "Team",
        "SESSIONS": "SESSION",
        "ENTRY": "Entry",
    }

    try:
        for t_name, col_name in tables_to_check.items():
            t = db.getTable(t_name)
            if not t:
                print(f"Table {t_name} not found.")
                continue

            try:
                col = t.getColumn(col_name)
                is_auto = col.isAutoNumber()
                dtype = col.getType()
                print(
                    f"Table: {t_name:10} | Col: {col_name:10} | "
                    f"AutoNumber: {str(is_auto):5} | Type: {dtype}"
                )
            except Exception as e:
                print(f"Column {col_name} not found in {t_name} or error: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    check_autonumber()
