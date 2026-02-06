import json
import os
import sys

# Add src path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(BASE_DIR, "../src"))
sys.path.append(SRC_DIR)

from mm_to_json import mdb_restorer  # noqa: E402

# Import converter script logic directly (if we renamed to module, easier,
# but for now subprocess or import)
# Reusing test_full_cycle logic for conversion run?
# Or just subprocess
CONVERTER_SCRIPT = os.path.join(SRC_DIR, "mm_to_json", "mm_to_json.py")
DUMP_SCRIPT = os.path.abspath(os.path.join(BASE_DIR, "../scripts/dump_mdb.py"))


def test_recreate_singers():
    print("Testing Recreation of Singers23.mdb...")

    # 1. Source files
    SOURCE_MDB = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "Singers23.mdb")
    # DUMP_JSON = os.path.join(BASE_DIR, "Singers23_dump.json") # Unused
    RECREATED_MDB = os.path.join(BASE_DIR, "Recreated.mdb")
    RECREATED_JSON_OUT = os.path.join(BASE_DIR, "Recreated_Export.json")
    ORIGINAL_JSON_OUT = os.path.join(BASE_DIR, "Original_Export.json")

    # Clean previous
    if os.path.exists(RECREATED_MDB):
        os.remove(RECREATED_MDB)

    # 2. Dump Original
    # SCRIPTS_DIR = os.path.dirname(DUMP_SCRIPT) # Unused
    RAW_DUMP = os.path.join(BASE_DIR, "Singers23_raw_dump.json")

    print(f"Dumping original MDB from {SOURCE_MDB}...")
    subprocess_run([sys.executable, DUMP_SCRIPT, SOURCE_MDB, RAW_DUMP])

    if not os.path.exists(RAW_DUMP):
        print("Dump failed.")
        return

    # 3. Restore to New MDB
    if os.path.exists(RECREATED_MDB):
        os.remove(RECREATED_MDB)

    print(f"Restoring to {RECREATED_MDB}...")
    mdb_restorer.restore_db(RAW_DUMP, RECREATED_MDB)

    # 4. Verify Content (Logic Check)
    # Run mm_to_json conversion on BOTH
    print("Running mm_to_json on Original...")
    subprocess_run([sys.executable, CONVERTER_SCRIPT, SOURCE_MDB, "-d", BASE_DIR])
    os.rename(os.path.join(BASE_DIR, "Singers23.json"), ORIGINAL_JSON_OUT)

    print("Running mm_to_json on Recreated...")
    subprocess_run([sys.executable, CONVERTER_SCRIPT, RECREATED_MDB, "-d", BASE_DIR])
    # Output name is Recreated.json
    os.rename(os.path.join(BASE_DIR, "Recreated.json"), RECREATED_JSON_OUT)

    # 5. Compare
    print("Comparing JSON exports...")
    with open(ORIGINAL_JSON_OUT, "r") as f1, open(RECREATED_JSON_OUT, "r") as f2:
        j1 = json.load(f1)
        j2 = json.load(f2)

    # Deep compare logic or string compare?
    # JSON dump ordering might differ if not sorted.
    # mm_to_json sorts events, sessions etc.
    s1 = json.dumps(j1, sort_keys=True)
    s2 = json.dumps(j2, sort_keys=True)

    if s1 == s2:
        print("SUCCESS: JSON exports match exactly.")
    else:
        print("FAILURE: JSON exports differ.")
        # Optional: Print diff

    print("Recreation Verification Complete.")


def subprocess_run(cmd, cwd=None):
    import subprocess

    subprocess.run(cmd, cwd=cwd, check=True)


if __name__ == "__main__":
    test_recreate_singers()
