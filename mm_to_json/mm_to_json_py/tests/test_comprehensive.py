import json
import os
import subprocess
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
TEST_DATA_MDB = os.path.join(BASE_DIR, "Sample_Data.mdb")
TEMPLATE_SCHEMA = os.path.join(BASE_DIR, "Template_Schema.json")  # Updated
GENERATOR_SCRIPT = os.path.join(SCRIPTS_DIR, "generate_sample_data.py")
DUMP_SCRIPT = os.path.join(SCRIPTS_DIR, "dump_mdb.py")
RESTORE_SCRIPT = os.path.join(SCRIPTS_DIR, "restore_mdb.py")
MM_TO_JSON_SCRIPT = os.path.join(PROJECT_ROOT, "src/mm_to_json/mm_to_json.py")

# Outputs
SAMPLE_DUMP_JSON = os.path.join(BASE_DIR, "Sample_Dump.json")
RESTORED_MDB = os.path.join(BASE_DIR, "Sample_Restored.mdb")
SAMPLE_EXPORT = os.path.join(BASE_DIR, "Sample_Export.json")
RESTORED_EXPORT = os.path.join(BASE_DIR, "Restored_Export.json")


def run_command(cmd, cwd=None):
    # Prepend uv run
    # Ensure cmd starts with python executable, replace it with 'uv run python'?
    # Or 'uv run script.py'.
    # cmd[0] is sys.executable usually.

    final_cmd = ["uv", "run"]
    # If first arg is python executable, skip it
    if cmd[0] == sys.executable:
        final_cmd.extend(cmd[1:])
    else:
        final_cmd.extend(cmd)

    print(f"Running: {' '.join(final_cmd)}")

    # Set UV_CACHE_DIR to local for sandbox
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = os.path.join(BASE_DIR, ".uv_cache")

    subprocess.run(final_cmd, check=True, cwd=cwd, env=env)


def run_test():
    print("=== STARTING COMPREHENSIVE PIPELINE TEST ===")

    # 1. Generate Sample Data
    print("\n--- Step 1: Generate Sample Data ---")
    run_command([sys.executable, GENERATOR_SCRIPT, TEMPLATE_SCHEMA, TEST_DATA_MDB])

    # 2. Dump Sample Data
    print("\n--- Step 2: Dump Sample Data ---")
    run_command([sys.executable, DUMP_SCRIPT, TEST_DATA_MDB, SAMPLE_DUMP_JSON])

    # 3. Restore Sample Data
    print("\n--- Step 3: Restore Sample Data ---")
    run_command([sys.executable, RESTORE_SCRIPT, SAMPLE_DUMP_JSON, RESTORED_MDB])

    # 4. Export Original Sample to JSON (mm_to_json)
    print("\n--- Step 4: Export Original Sample ---")
    # mm_to_json outputs to CWD/Filename.json
    run_command([sys.executable, MM_TO_JSON_SCRIPT, TEST_DATA_MDB], cwd=BASE_DIR)
    # Expected output: Sample_Data.json
    expected_out = os.path.join(BASE_DIR, "Sample_Data.json")
    if os.path.exists(expected_out):
        os.rename(expected_out, SAMPLE_EXPORT)
    else:
        print(f"Error: {expected_out} not found.")
        sys.exit(1)

    # 5. Export Restored to JSON
    print("\n--- Step 5: Export Restored Sample ---")
    run_command([sys.executable, MM_TO_JSON_SCRIPT, RESTORED_MDB], cwd=BASE_DIR)
    # Expected output: Sample_Restored.json
    expected_out_2 = os.path.join(BASE_DIR, "Sample_Restored.json")
    if os.path.exists(expected_out_2):
        os.rename(expected_out_2, RESTORED_EXPORT)
    else:
        print(f"Error: {expected_out_2} not found.")
        sys.exit(1)

    # 6. Compare/Verify
    print("\n--- Step 6: Verify ---")
    with open(SAMPLE_EXPORT, "r") as f1, open(RESTORED_EXPORT, "r") as f2:
        j1 = json.load(f1)
        j2 = json.load(f2)

    # Compare keys?
    # Or strict equality?
    # Note: Row order might differ if not sorted.
    # mm_to_json sorts events by event number? Yes.
    # Entry order? sort entries?

    # Let's try strict equality first
    if json.dumps(j1, sort_keys=True) == json.dumps(j2, sort_keys=True):
        print("SUCCESS: JSON exports match exactly.")
    else:
        print("FAILURE: JSON exports differ.")
        # Optional: Print diff keys
        pass


if __name__ == "__main__":
    run_test()
