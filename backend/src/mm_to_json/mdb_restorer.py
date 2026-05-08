import json
import logging
import os

from mm_to_json import mdb_writer

logger = logging.getLogger(__name__)


def restore_db(json_path, target_mdb):
    """
    Restores an MDB file from a JSON dump.
    """
    print(f"Restoring {target_mdb} from {json_path}...")

    with open(json_path) as f:
        dump_data = json.load(f)

    mdb_writer.ensure_jvm_started()

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
    db = DatabaseBuilder.create(Database.FileFormat.V2000, File(target_mdb))

    try:
        tables = dump_data.get("tables", {})
        for table_name, table_def in tables.items():
            rows = table_def.get("rows", [])
            print(f"Creating table {table_name} with {len(rows)} rows...")

            tb = TableBuilder(table_name)

            # Add Columns
            columns = table_def.get("columns", [])
            for col in columns:
                dtype_str = col["type"]
                try:
                    dtype = getattr(DataType, dtype_str)
                except AttributeError:
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
                    continue

                ib = IndexBuilder(idx["name"])
                if idx.get("unique"):
                    ib.setUnique()
                for cname in idx.get("columns", []):
                    ib.addColumns([cname])
                tb.addIndex(ib)

            # Create Table
            table = tb.toTable(db)

            # Enable AutoNumber Insert if applicable
            has_auto = any(col.get("auto_number") for col in columns)
            if has_auto:
                table.setAllowAutoNumberInsert(True)

            # Map column name (lowercase) to info for coercion
            col_info = {}
            for col in columns:
                col_info[col["name"].lower()] = {
                    "type": getattr(DataType, col["type"], DataType.TEXT),
                    "original_name": col["name"],
                }

            # Insert Rows
            if rows:
                print(f"  Inserting {len(rows)} rows into {table_name}...")
                from java.util import HashMap

                for row_data in rows:
                    row_map = HashMap()
                    for k, v in row_data.items():
                        if table_name == "SESSIONS" and k == "DAY" and v is None:
                            v = 1

                        if v is None:
                            row_map.put(k, None)
                        else:
                            kl = str(k).lower()
                            info = col_info.get(kl)
                            if not info:
                                row_map.put(k, str(v))
                                continue

                            dtype = info["type"]
                            dtype_name = str(dtype.name())

                            if dtype_name in (
                                "LONG",
                                "INT",
                                "BYTE",
                                "NUMERIC",
                                "MONEY",
                                "BIG_INT",
                            ):
                                try:
                                    row_map.put(k, int(float(v)))
                                except Exception:
                                    row_map.put(k, v)

                            elif dtype_name in ("DOUBLE", "FLOAT"):
                                try:
                                    row_map.put(k, float(v))
                                except Exception:
                                    row_map.put(k, v)

                            elif dtype_name == "TEXT":
                                try:
                                    col = None
                                    for c in table.getColumns():
                                        if str(c.getName()).lower() == kl:
                                            col = c
                                            break

                                    if col:
                                        phys_name = str(col.getName())
                                        max_len = col.getLength()
                                        s_val = str(v)
                                        if len(s_val) > max_len:
                                            row_map.put(phys_name, s_val[:max_len])
                                        else:
                                            row_map.put(phys_name, s_val)
                                    else:
                                        row_map.put(k, str(v))
                                except Exception:
                                    row_map.put(k, str(v))

                            elif dtype_name == "MEMO":
                                row_map.put(k, str(v))

                            elif dtype_name == "BOOLEAN":
                                if isinstance(v, str):
                                    row_map.put(k, v.lower() == "true")
                                else:
                                    row_map.put(k, bool(v))

                            elif dtype_name == "SHORT_DATE_TIME":
                                try:
                                    from java.util import Date

                                    if isinstance(v, (int, float)):
                                        row_map.put(k, Date(int(v)))
                                    else:
                                        from datetime import datetime

                                        dt = datetime.fromisoformat(
                                            str(v).replace("Z", "+00:00")
                                        )
                                        ts_ms = int(dt.timestamp() * 1000)
                                        row_map.put(k, Date(ts_ms))
                                except Exception:
                                    row_map.put(k, None)

                            elif dtype_name in ("BINARY", "OLE"):
                                try:
                                    import base64

                                    row_map.put(k, base64.b64decode(v))
                                except Exception:
                                    row_map.put(k, None)

                            else:
                                row_map.put(k, str(v))

                    table.addRowFromMap(row_map)
    finally:
        db.close()
    print("Restore complete.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", help="Path to JSON dump")
    parser.add_argument("target_mdb", help="Output MDB path")
    args = parser.parse_args()

    restore_db(args.json_path, args.target_mdb)
