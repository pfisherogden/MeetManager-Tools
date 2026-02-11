import json

from mm_to_json import mdb_writer


def restore_db(json_path, target_mdb):
    """
    Restores an MDB file from a JSON dump.
    """
    print(f"Restoring {target_mdb} from {json_path}...")

    with open(json_path) as f:
        dump_data = json.load(f)

    start_jvm()

    from com.healthmarketscience.jackcess import (
        ColumnBuilder,
        Database,
        DatabaseBuilder,
        DataType,
        IndexBuilder,
        TableBuilder,
    )
    from java.io import File

    # Create new MDB
    # Format: V2000 is typical for .mdb
    db = DatabaseBuilder.create(Database.FileFormat.V2000, File(target_mdb))

    try:
        tables = dump_data.get("tables", {})
        for table_name, table_def in tables.items():
            print(f"Creating table {table_name}...")

            tb = TableBuilder(table_name)

            # Add Columns
            columns = table_def.get("columns", [])
            for col in columns:
                # Map type string to DataType
                # e.g. "LONG" -> DataType.LONG
                dtype_str = col["type"]
                try:
                    dtype = getattr(DataType, dtype_str)
                except AttributeError:
                    print(f"Warning: Unknown type {dtype_str} for {col['name']}, defaulting to TEXT")
                    dtype = DataType.TEXT

                cb = ColumnBuilder(col["name"])
                cb.setType(dtype)

                if col.get("length"):
                    cb.setLength(col["length"])
                if col.get("precision"):
                    cb.setPrecision(col["precision"])
                if col.get("scale"):
                    cb.setScale(col["scale"])
                if col.get("auto_number"):
                    cb.setAutoNumber(True)

                tb.addColumn(cb)

            # Add Indexes
            indexes = table_def.get("indexes", [])
            for idx in indexes:
                if idx["name"].startswith("."):
                    # Skip internal/system indexes
                    continue

                ib = IndexBuilder(idx["name"])
                if idx.get("unique"):
                    ib.setUnique()
                for cname in idx.get("columns", []):
                    ib.addColumns([cname])  # accepts varargs or string array
                tb.addIndex(ib)

            # Create Table
            table = tb.toTable(db)

            # Enable AutoNumber Insert if applicable
            has_auto = any(col.get("auto_number") for col in columns)
            if has_auto:
                table.setAllowAutoNumberInsert(True)

            # Map column name to type for coercion
            col_types = {}
            for col in columns:
                col_types[col["name"]] = getattr(DataType, col["type"], DataType.TEXT)

            # Insert Rows
            rows = table_def.get("rows", [])
            if rows:
                print(f"  Inserting {len(rows)} rows...")
                # Jackcess can add rows from map
                from java.util import HashMap

                for row_data in rows:
                    row_map = HashMap()
                    for k, v in row_data.items():
                        if table_name == "SESSIONS" and k == "DAY" and v is None:
                            v = 1  # Fix for mm_to_json crash on null DAY

                        if v is None:
                            row_map.put(k, None)
                        else:
                            # Coerce based on type
                            dtype = col_types.get(k, DataType.TEXT)

                            # Numeric types
                            if dtype in (
                                DataType.LONG,
                                DataType.INT,
                                DataType.BYTE,
                                DataType.NUMERIC,
                                DataType.MONEY,
                                DataType.BIG_INT,
                            ):
                                try:
                                    # Handle "123.0" if float in string?
                                    row_map.put(k, int(float(v)))
                                except Exception:
                                    row_map.put(k, v)  # Fallback

                            elif dtype in (DataType.DOUBLE, DataType.FLOAT):
                                try:
                                    row_map.put(k, float(v))
                                except Exception:
                                    row_map.put(k, v)

                            elif dtype == DataType.BOOLEAN:
                                # "True"/"False" or 1/0
                                if isinstance(v, str):
                                    row_map.put(k, v.lower() == "true")
                                else:
                                    row_map.put(k, bool(v))

                            elif dtype == DataType.SHORT_DATE_TIME:
                                # v is long timestamp
                                # create java.util.Date(v)
                                try:
                                    from java.util import Date

                                    row_map.put(k, Date(int(v)))
                                except Exception:
                                    row_map.put(k, None)

                            else:
                                row_map.put(k, str(v))

                    table.addRowFromMap(row_map)

    finally:
        db.close()
    print("Restore complete.")


def start_jvm():
    mdb_writer.ensure_jvm_started()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", help="Path to JSON dump")
    parser.add_argument("target_mdb", help="Output MDB path")
    args = parser.parse_args()

    restore_db(args.json_path, args.target_mdb)
