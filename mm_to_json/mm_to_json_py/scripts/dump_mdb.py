import base64
import json
import os
import sys

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from mm_to_json import mdb_writer


def dump_db(mdb_path, output_json):
    print(f"Dumping {mdb_path} to {output_json}...")
    db = mdb_writer.open_db(mdb_path)

    dump_data = {"tables": {}}

    try:
        # Iterate all tables
        for table_name_obj in db.getTableNames():
            table_name = str(table_name_obj)
            print(f"Processing {table_name}...")
            t = db.getTable(table_name)

            # Schema
            columns = []
            for col in t.getColumns():
                col_def = {
                    "name": str(col.getName()),
                    "type": str(col.getType()),
                    "length": int(col.getLength()),  # Ensure int
                    "precision": int(col.getPrecision()),
                    "scale": int(col.getScale()),
                    "auto_number": bool(col.isAutoNumber()),
                }
                columns.append(col_def)

            # Indexes (Simplified: just names and uniqueness for now)
            indexes = []
            for idx in t.getIndexes():
                idx_def = {
                    "name": str(idx.getName()),
                    "unique": idx.isUnique(),
                    "columns": [str(c.getName()) for c in idx.getColumns()],
                }
                indexes.append(idx_def)

            # Data
            rows = []
            for row in t:
                # Jackcess returns Map<String, Object>.
                # Need to convert values to JSON serializable.
                row_data = {}
                for col in columns:
                    cname = col["name"]
                    val = row.get(cname)

                    if val is None:
                        row_data[cname] = None
                    elif isinstance(val, (int, float, str, bool)):
                        row_data[cname] = val
                    else:
                        # Handle Date, Bytes, etc.
                        # Java Dates/Time -> Long timestamp
                        type_name = str(type(val))
                        if "Date" in type_name:
                            row_data[cname] = val.getTime()
                        elif "byte[]" in type_name or "jarray" in type_name:  # JPype byte array
                            # Need to convert byte[] to hex or base64
                            # JPype byte array to python bytes
                            try:
                                b = bytes(val)
                                row_data[cname] = base64.b64encode(b).decode("ascii")
                            except Exception:
                                row_data[cname] = str(val)
                        else:
                            row_data[cname] = str(val)

                rows.append(row_data)

            dump_data["tables"][table_name] = {"columns": columns, "indexes": indexes, "rows": rows}

    finally:
        db.close()

    with open(output_json, "w") as f:
        json.dump(dump_data, f, indent=2)
    print("Dump complete.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("mdb_path", help="Input MDB file")
    parser.add_argument("json_out", help="Output JSON file")
    args = parser.parse_args()

    if not os.path.exists(args.mdb_path):
        print(f"File not found: {args.mdb_path}")
        sys.exit(1)

    dump_db(args.mdb_path, args.json_out)
