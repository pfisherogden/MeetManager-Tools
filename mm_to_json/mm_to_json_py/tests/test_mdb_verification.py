import glob
import json
import os
import shutil
import sys
from datetime import datetime

# Adjust paths to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
scripts_dir = os.path.join(project_root, "scripts")
src_dir = os.path.join(project_root, "src")

sys.path.append(scripts_dir)
sys.path.append(src_dir)

# Import tools
try:
    from dump_mdb import dump_db

    from mm_to_json import mdb_restorer
except ImportError as e:
    print(f"Error importing modules: {e}")
    print(f"Sys Path: {sys.path}")
    sys.exit(1)

# Configuration
# MDBs are in ../../tmp/Swim Meets/ relative to project_root (mm_to_json_py)
# Actually project root is mm_to_json/mm_to_json_py
# Data is in mm_to_json/tmp (subfolders SwimMeetsYYYY)
DATA_DIR = os.path.abspath(os.path.join(project_root, "../tmp"))
OUTPUT_DIR = os.path.join(project_root, "verification_output")
REPORT_FILE = os.path.join(project_root, "verification_report.md")


class MdbDiffer:
    def __init__(self):
        self.schema_registry = {}  # {table_name: {col_name: type}}
        self.results = []

    def load_json(self, path):
        with open(path, "r") as f:
            return json.load(f)

    def compare_jsons(self, json1, json2):
        """
        Compare two JSON dumps. Returns list of differences.
        Focuses on data content.
        """
        diffs = []
        tables1 = set(json1.get("tables", {}).keys())
        tables2 = set(json2.get("tables", {}).keys())

        if tables1 != tables2:
            missing = tables1 - tables2
            extra = tables2 - tables1
            if missing:
                diffs.append(f"Missing tables in copy: {missing}")
            if extra:
                diffs.append(f"Extra tables in copy: {extra}")

        common_tables = tables1.intersection(tables2)
        for t in common_tables:
            rows1 = json1["tables"][t]["rows"]
            rows2 = json2["tables"][t]["rows"]

            # Simple count check
            if len(rows1) != len(rows2):
                diffs.append(
                    f"Table {t} row count mismatch: Original={len(rows1)}, Copy={len(rows2)}"
                )
                continue

            # Deep compare (expensive but necessary for full verification)
            # Dumps are lists of dicts. Order typically preserved by dump_mdb if no PK,
            # but let's assume raw dump order is consistent.
            # Ideally we'd sort by PK, but PKs might be complex.
            # We'll try direct index comparison first.
            for i, (r1, r2) in enumerate(zip(rows1, rows2)):
                if r1 != r2:
                    # Find first diff
                    row_diffs = []
                    all_keys = set(r1.keys()) | set(r2.keys())
                    for k in all_keys:
                        v1 = r1.get(k)
                        v2 = r2.get(k)
                        if v1 != v2:
                            # Allow some tolerance for floats or timestamps?
                            # dump_mdb converts dates to long.
                            row_diffs.append(f"{k}: {v1} != {v2}")

                    if row_diffs:
                        diffs.append(f"Table {t} Row {i} mismatch: {', '.join(row_diffs[:5])}")
                        if len(diffs) > 20:
                            diffs.append("... too many errors")
                            return diffs

        return diffs

    def register_schema(self, mdb_name, json_data):
        tables = json_data.get("tables", {})
        for t_name, t_def in tables.items():
            if t_name not in self.schema_registry:
                self.schema_registry[t_name] = {"seen_in": [], "columns": {}}

            self.schema_registry[t_name]["seen_in"].append(mdb_name)

            for col in t_def.get("columns", []):
                c_name = col["name"]
                c_type = col["type"]
                if c_name not in self.schema_registry[t_name]["columns"]:
                    self.schema_registry[t_name]["columns"][c_name] = c_type

    def run_comparison(self, mdb_path):
        name = os.path.basename(mdb_path)
        print(f"Verifying {name}...")

        rel_path = os.path.relpath(mdb_path, DATA_DIR)
        safe_name = rel_path.replace("/", "_").replace("\\", "_").replace(" ", "_")

        out_base = os.path.join(OUTPUT_DIR, safe_name)
        os.makedirs(out_base, exist_ok=True)

        json_orig = os.path.join(out_base, "original.json")
        mdb_copy = os.path.join(out_base, "restored.mdb")
        json_copy = os.path.join(out_base, "restored.json")

        try:
            # 1. Dump Original
            dump_db(mdb_path, json_orig)
            data_orig = self.load_json(json_orig)

            # Record Schema
            self.register_schema(name, data_orig)

            # 2. Restore to new MDB
            if os.path.exists(mdb_copy):
                os.remove(mdb_copy)
            mdb_restorer.restore_db(json_orig, mdb_copy)

            # 3. Dump Restored
            dump_db(mdb_copy, json_copy)
            data_copy = self.load_json(json_copy)

            # 4. Compare
            diffs = self.compare_jsons(data_orig, data_copy)

            status = "PASS" if not diffs else "FAIL"
            self.results.append({"file": rel_path, "status": status, "errors": diffs})
            print(f"  Result: {status}")

        except Exception as e:
            print(f"  Result: EXCEPTION - {e}")
            import traceback

            traceback.print_exc()
            self.results.append({"file": rel_path, "status": "EXCEPTION", "errors": [str(e)]})

    def generate_report(self):
        lines = []
        lines.append("# MDB Verification Report")
        lines.append(f"Date: {datetime.now()}")
        lines.append("")

        lines.append("## Round-Trip Results")
        lines.append("| File | Status | Notes |")
        lines.append("|---|---|---|")
        for r in self.results:
            note = "<br>".join(r["errors"][:5]) if r["errors"] else ""
            if len(r["errors"]) > 5:
                note += "<br>..."
            lines.append(f"| {r['file']} | {r['status']} | {note} |")

        lines.append("")
        lines.append("## Schema Analysis")
        lines.append("Tables found across all MDBs:")

        sorted_tables = sorted(self.schema_registry.keys())
        for t in sorted_tables:
            info = self.schema_registry[t]
            lines.append(f"### Table: `{t}`")
            lines.append(f"Found in {len(info['seen_in'])} files.")
            lines.append("Columns:")
            cols = sorted(info["columns"].items())
            lines.append("| Column | Type |")
            lines.append("|---|---|")
            for c_name, c_type in cols:
                lines.append(f"| {c_name} | {c_type} |")
            lines.append("")

        with open(REPORT_FILE, "w") as f:
            f.write("\n".join(lines))
        print(f"Report written to {REPORT_FILE}")


def main():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    differ = MdbDiffer()

    # Recursively find .mdb files
    # Using glob for recursion
    # glob.glob("path/**/*.mdb", recursive=True)
    pattern = os.path.join(DATA_DIR, "**", "*.mdb")
    mdb_files = glob.glob(pattern, recursive=True)

    print(f"Found {len(mdb_files)} MDB files in {DATA_DIR}")

    for mdb in mdb_files:
        differ.run_comparison(mdb)

    differ.generate_report()


if __name__ == "__main__":
    main()
