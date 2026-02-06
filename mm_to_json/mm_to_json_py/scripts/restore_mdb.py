import os
import sys

# Add src to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, "../src"))
sys.path.append(SRC_DIR)

from mm_to_json import mdb_restorer  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run restore_mdb.py <input.json> <output.mdb>")
        sys.exit(1)

    json_path = sys.argv[1]
    mdb_path = sys.argv[2]

    if os.path.exists(mdb_path):
        os.remove(mdb_path)

    mdb_restorer.restore_db(json_path, mdb_path)
