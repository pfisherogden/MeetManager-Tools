import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from mm_to_json.mm_to_json import MmToJsonConverter

def test_export_full_schema_handles_unknown_tables(tmp_path):
    """Verify that export_full_schema doesn't crash on unexpected tables/columns."""
    # Create a real dummy file so init passes
    dummy_mdb = tmp_path / "dummy.mdb"
    dummy_mdb.write_text("dummy")
    
    # We mock the Jackcess Database object
    mock_db = MagicMock()
    mock_db.getTableNames.return_value = ["NewTable"]
    
    mock_table = MagicMock()
    mock_col = MagicMock()
    mock_col.getName.return_value = "Strange_Column"
    mock_col.getType().name.return_value = "TEXT"
    mock_col.getLength.return_value = 255
    mock_col.getPrecision.return_value = 0
    mock_col.getScale.return_value = 0
    mock_col.isAutoNumber.return_value = False
    
    mock_table.getColumns.return_value = [mock_col]
    mock_table.getIndexes.return_value = []
    # Mock iterator for table rows
    mock_table.__iter__.return_value = [{"Strange_Column": "Value"}]
    
    mock_db.getTable.return_value = mock_table
    
    # Patch ensure_jvm_started to avoid JRE requirement in this test
    with patch("mm_to_json.mdb_writer.ensure_jvm_started"):
        conv = MmToJsonConverter(mdb_path=str(dummy_mdb))
        conv.db = mock_db
        
        schema = conv.export_full_schema()
        
        assert "NewTable" in schema["tables"]
        assert schema["tables"]["NewTable"]["columns"][0]["name"] == "Strange_Column"

@patch("mm_to_json.mdb_writer.ensure_jvm_started")
@patch("mm_to_json.mdb_writer.create_db")
def test_mdb_restorer_compatibility(mock_create, mock_jvm, tmp_path):
    """Verify that mdb_restorer can handle the schema dictionary."""
    from mm_to_json.mdb_restorer import restore_db
    
    schema_data = {
        "tables": {
            "MEET": {
                "columns": [
                    {"name": "meet_name1", "type": "TEXT", "length": 255, "precision": 0, "scale": 0, "auto_number": False}
                ],
                "indexes": [],
                "rows": [{"meet_name1": "Test"}]
            }
        }
    }
    
    # Write mock schema to temp file
    temp_json = tmp_path / "schema.json"
    temp_json.write_text(json.dumps(schema_data))
    
    target_mdb = tmp_path / "output.mdb"
        
    restore_db(str(temp_json), str(target_mdb))
    
    # Verify that mdb_writer.create_db was called
    assert mock_create.called
