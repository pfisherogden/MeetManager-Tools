import mdb_writer


def check_meet_id():
    mdb_path = "../Singers23.mdb"
    db = mdb_writer.open_db(mdb_path)
    try:
        t = db.getTable("SESSIONS")
        print(f"SESSIONS rows: {t.getRowCount()}")
        for row in t:
            print(f"Session: {row.get('SESSION')}, MeetID: {row.get('MEETID')}")
            break  # Just need one

    finally:
        db.close()


if __name__ == "__main__":
    check_meet_id()
