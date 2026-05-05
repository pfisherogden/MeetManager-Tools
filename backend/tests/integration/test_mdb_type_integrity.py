
import os
import sys
import json
import tempfile
import pytest
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.mdb_restorer import restore_db

def test_mdb_date_and_type_integrity(tmp_path):
    """
    Verifies that various data types (Dates, Booleans, Numbers) are preserved 
    correctly through the MDB -> JSON -> MDB cycle.
    """
    # Use the template MDB as a base
    template_path = "/app/season-setup/template_unzip/swmeets7/Summer League Meet Template.mdb"
    if not os.path.exists(template_path):
        pytest.skip("Template MDB not found in container")

    # 1. Export schema and rows from template
    conv = MmToJsonConverter(mdb_path=template_path)
    full_schema = conv.export_full_schema()
    
    # 2. Modify some values to test different types
    # Meet Name (Text)
    meet_table = full_schema["tables"]["Meet"]
    meet_table["rows"][0]["Meet_name1"] = "Type Integrity Test"
    
    # Dates (Short Date/Time)
    # Testing both millisecond timestamp AND ISO string (which to_python produces)
    test_date_ms = 1780099200000 # 2026-05-30
    test_date_iso = "2026-06-01T00:00:00"
    
    meet_table["rows"][0]["Meet_start"] = test_date_ms
    meet_table["rows"][0]["Meet_end"] = test_date_iso
    
    # Booleans
    meet_table["rows"][0]["A_Relaysonly"] = True
    meet_table["rows"][0]["Use_hometown"] = False
    
    # 3. Save to JSON
    json_path = tmp_path / "test_schema.json"
    with open(json_path, "w") as f:
        json.dump(full_schema, f, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else x)

    # 4. Restore to new MDB
    target_mdb = tmp_path / "restored_test.mdb"
    restore_db(str(json_path), str(target_mdb))
    
    # 5. Load back and verify
    restored_conv = MmToJsonConverter(mdb_path=str(target_mdb))
    rm_df = restored_conv.tables.get("meet")
    assert rm_df is not None and not rm_df.empty
    rm = rm_df.iloc[0]
    
    # Verify Text
    assert rm.get("meet_name1") == "Type Integrity Test"
    
    # Verify Dates
    def get_ts(val):
        if hasattr(val, 'timestamp'): return int(val.timestamp() * 1000)
        return val

    check_start = get_ts(rm.get("meet_start"))
    assert check_start == test_date_ms
    
    check_end = get_ts(rm.get("meet_end"))
    assert check_end == 1780272000000 # ISO 2026-06-01
    
    # Verify Booleans
    assert bool(rm.get("a_relaysonly")) is True
    assert bool(rm.get("use_hometown")) is False
