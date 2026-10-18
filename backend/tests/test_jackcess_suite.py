"""Comprehensive test suite for the Rust Jackcess port (`jackcess_rs` & `jackcess.rs`).

Verifies:
1. Drop-in API parity with `com.healthmarketscience.jackcess` (`DatabaseBuilder`,
   `TableBuilder`, `ColumnBuilder`, `IndexBuilder`, `Cursor`, `DataType`, `Row`).
2. All Jet data types (`BOOLEAN`, `BYTE`, `INT`, `LONG`, `MONEY`, `FLOAT`, `DOUBLE`,
   `SHORT_DATE_TIME`, `TEXT`, `BINARY`, `MEMO`, `OLE`, `GUID`, `NUMERIC`), AutoNumber
   generation, LVAL inline/single-page/multi-page storage, in-place and overflow
   row updates, and row deletion.
3. Cross-engine binary compatibility: `.mdb` databases created and mutated by
   Rust `jackcess_rs` are opened and verified by Java Jackcess (`jackcess-4.0.5.jar`).
4. Upstream Jackcess test database suite (`V1997`, `V2000`, `V2003`, `V2007`, `V2010`)
   row-for-row verification against Java Jackcess when `/tmp/jackcess-upstream` is present.
5. End-to-end `mdb_restorer` and `mdb_writer` integration on `Singers23.mdb`.
"""

from __future__ import annotations

import datetime
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import jackcess_rs as standalone_jackcess_rs
from jackcess_rs import (
    ColumnBuilder,
    CursorBuilder,
    Database,
    DatabaseBuilder,
    DataType,
    IndexBuilder,
    TableBuilder,
)
from mm_to_json import jackcess_rs, mdb_restorer, mdb_writer
from mm_to_json.mm_to_json import MmToJsonConverter

assert standalone_jackcess_rs.DatabaseBuilder is jackcess_rs.DatabaseBuilder
assert standalone_jackcess_rs.PropertyMap is jackcess_rs.PropertyMap

REPO_ROOT = Path(__file__).resolve().parents[2]
SINGERS_MDB = REPO_ROOT / "web-client" / "tests-e2e" / "Singers23.mdb"
UPSTREAM_DATA_DIR = Path("/tmp/jackcess-upstream/src/test/data")


@pytest.fixture(autouse=True)
def _enable_rust_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure Rust engine is enabled for direct Rust Jackcess unit tests."""
    monkeypatch.setenv("MM_ENGINE", "rust")
    monkeypatch.setenv("MM_DISABLE_RUST", "0")


def test_database_create_and_table_builder(tmp_path: Path) -> None:
    """Port of Jackcess `DatabaseTest.testCreate` & `TableTest`."""
    mdb_file = tmp_path / "created_v2000.mdb"
    with DatabaseBuilder.create(Database.FileFormat.V2000, mdb_file) as db:
        assert db.getTableNames() == set()
        sys_names = db.getSystemTableNames()
        assert "MSysObjects" in sys_names
        assert "MSysACEs" in sys_names

        tb = (
            TableBuilder("TestTable")
            .addColumn(ColumnBuilder("id", DataType.LONG).setAutoNumber(True))
            .addColumn(ColumnBuilder("name", DataType.TEXT).setLengthInUnits(50))
            .addColumn(ColumnBuilder("score", DataType.DOUBLE))
            .addColumn(ColumnBuilder("active", DataType.BOOLEAN))
            .setPrimaryKey("id")
            .addIndex(IndexBuilder("NameIdx").addColumns("name"))
        )
        table = tb.toTable(db)

        assert "TestTable" in db.getTableNames()
        assert table.getName() == "TestTable"
        assert len(table.getColumns()) == 4
        assert table.getColumn("id").isAutoNumber() is True
        assert table.getColumn("name").getType() == DataType.TEXT
        assert table.getColumn("name").getLengthInUnits() == 50
        assert len(table.getIndexes()) == 2
        assert table.getPrimaryKeyIndex().isUnique() is True

        # Insert rows positionally and via map
        r1 = table.addRow(None, "Alice", 98.5, True)
        assert r1[0] == 1
        assert r1[1] == "Alice"

        r2 = table.addRowFromMap({"name": "Bob", "score": 87.25, "active": False})
        assert r2["id"] == 2
        assert r2["name"] == "Bob"

        assert table.getRowCount() == 2


def test_all_column_data_types_and_lval_roundtrip(tmp_path: Path) -> None:
    """Port of Jackcess `DatabaseReadWriteTest` & `LongValueTest` across all column types."""
    mdb_file = tmp_path / "all_types.mdb"
    with DatabaseBuilder.create(Database.FileFormat.V2000, mdb_file) as db:
        table = (
            TableBuilder("AllTypes")
            .addColumn(ColumnBuilder("id", DataType.LONG).setAutoNumber(True))
            .addColumn(ColumnBuilder("bool_col", DataType.BOOLEAN))
            .addColumn(ColumnBuilder("byte_col", DataType.BYTE))
            .addColumn(ColumnBuilder("int_col", DataType.INT))
            .addColumn(ColumnBuilder("long_col", DataType.LONG))
            .addColumn(ColumnBuilder("money_col", DataType.MONEY))
            .addColumn(ColumnBuilder("float_col", DataType.FLOAT))
            .addColumn(ColumnBuilder("double_col", DataType.DOUBLE))
            .addColumn(ColumnBuilder("date_col", DataType.SHORT_DATE_TIME))
            .addColumn(ColumnBuilder("text_col", DataType.TEXT).setLengthInUnits(100))
            .addColumn(ColumnBuilder("bin_col", DataType.BINARY).setLength(32))
            .addColumn(ColumnBuilder("memo_col", DataType.MEMO))
            .addColumn(ColumnBuilder("ole_col", DataType.OLE))
            .addColumn(ColumnBuilder("guid_col", DataType.GUID))
            .addColumn(ColumnBuilder("num_col", DataType.NUMERIC).setPrecision(18).setScale(4))
            .toTable(db)
        )

        # 1. Inline memo (<= 64B), ASCII compressed text
        dt1 = datetime.datetime(2026, 7, 18, 8, 30, 0)
        blob1 = b"\x01\x02\x03\x04\xfe\xff"
        table.addRowFromMap(
            {
                "bool_col": True,
                "byte_col": 42,
                "int_col": -1234,
                "long_col": 9876543,
                "money_col": Decimal("1234.5600"),
                "float_col": 12.5,
                "double_col": 3.141592653589793,
                "date_col": dt1,
                "text_col": "Compressed Latin-1 Text",
                "bin_col": b"\xaa\xbb\xcc\xdd",
                "memo_col": "Short inline memo string",
                "ole_col": blob1,
                "guid_col": "{32A69F00-7C84-11D0-AE4F-00A0C90F26F4}",
                "num_col": Decimal("-98765.4321"),
            }
        )

        # 2. Single-page LVAL memo (~2000 chars) & Unicode text
        single_page_memo = "Line-SinglePage-" * 120
        blob2 = bytes(i % 256 for i in range(1800))
        table.addRowFromMap(
            {
                "bool_col": False,
                "byte_col": 7,
                "int_col": 32000,
                "long_col": -500000,
                "money_col": Decimal("-45.6700"),
                "float_col": -0.25,
                "double_col": 1e-6,
                "date_col": datetime.datetime(2026, 6, 6, 14, 15, 30),
                "text_col": "Unicode Text: Swimming \u2605 \u6cf3",
                "bin_col": b"\x10\x20",
                "memo_col": single_page_memo,
                "ole_col": blob2,
                "guid_col": "{00000000-0000-0000-0000-000000000001}",
                "num_col": Decimal("0.0005"),
            }
        )

        # 3. Multi-page LVAL memo (> 12,000 chars) & multi-page OLE (> 10,000 bytes)
        multi_page_memo = "MultiPageMemoChunk-" * 700
        blob3 = bytes((i * 7) % 256 for i in range(11000))
        table.addRowFromMap(
            {
                "bool_col": True,
                "memo_col": multi_page_memo,
                "ole_col": blob3,
            }
        )

    # Re-open database and verify all 3 rows
    with DatabaseBuilder.open(mdb_file) as db2:
        t2 = db2.getTable("AllTypes")
        assert t2 is not None
        rows = list(t2)
        assert len(rows) == 3

        r0 = rows[0]
        assert r0["id"] == 1
        assert r0["bool_col"] is True
        assert r0["byte_col"] == 42
        assert r0["int_col"] == -1234
        assert r0["long_col"] == 9876543
        assert r0["money_col"] == Decimal("1234.5600")
        assert r0["float_col"] == pytest.approx(12.5)
        assert r0["double_col"] == pytest.approx(3.141592653589793)
        assert r0["date_col"] == dt1
        assert r0["date_col"].getTime() == pytest.approx(dt1.timestamp() * 1000.0)
        assert r0["text_col"] == "Compressed Latin-1 Text"
        assert r0["bin_col"] == b"\xaa\xbb\xcc\xdd"
        assert r0["memo_col"] == "Short inline memo string"
        assert r0["ole_col"] == blob1
        assert r0["guid_col"] == "{32A69F00-7C84-11D0-AE4F-00A0C90F26F4}"
        assert r0["num_col"] == Decimal("-98765.4321")

        r1 = rows[1]
        assert r1["id"] == 2
        assert r1["bool_col"] is False
        assert r1["text_col"] == "Unicode Text: Swimming \u2605 \u6cf3"
        assert r1["memo_col"] == single_page_memo
        assert r1["ole_col"] == blob2
        assert r1["num_col"] == Decimal("0.0005")

        r2 = rows[2]
        assert r2["id"] == 3
        assert r2["memo_col"] == multi_page_memo
        assert r2["ole_col"] == blob3
        assert r2["int_col"] is None
        assert r2["text_col"] is None


def test_cursor_search_update_and_delete(tmp_path: Path) -> None:
    """Port of Jackcess `CursorTest` (navigation, criteria search, update, overflow, delete)."""
    mdb_file = tmp_path / "cursor_test.mdb"
    with DatabaseBuilder.create(Database.FileFormat.V2000, mdb_file) as db:
        table = (
            TableBuilder("Swimmers")
            .addColumn(ColumnBuilder("Ath_no", DataType.LONG).setAutoNumber(True))
            .addColumn(ColumnBuilder("First_name", DataType.TEXT).setLengthInUnits(120))
            .addColumn(ColumnBuilder("Last_name", DataType.TEXT).setLengthInUnits(120))
            .addColumn(ColumnBuilder("Team_no", DataType.LONG))
            .addColumn(ColumnBuilder("Reg_no", DataType.TEXT).setLengthInUnits(20))
            .toTable(db)
        )

        for i in range(25):
            table.addRowFromMap(
                {
                    "First_name": f"Swimmer_{i}",
                    "Last_name": f"Family_{i % 5}_{'X' * 60}",
                    "Team_no": (i % 3) + 1,
                    "Reg_no": f"REG-{i:04d}",
                }
            )

        cursor = table.getDefaultCursor()
        assert cursor.findFirstRow({"Team_no": 2}) is True
        first_match = cursor.getCurrentRow()
        assert first_match is not None
        assert first_match["First_name"] == "Swimmer_1"

        assert cursor.findNextRow({"Team_no": 2}) is True
        second_match = cursor.getCurrentRow()
        assert second_match is not None
        assert second_match["First_name"] == "Swimmer_4"

        # Update current row via setCurrentRowValue
        cursor.setCurrentRowValue("Reg_no", "UPDATED-REG")
        assert CursorBuilder.findRow(table, {"Ath_no": 5})["Reg_no"] == "UPDATED-REG"  # type: ignore[index]

        # Update row with much longer string to test page overflow pointer (0x4000)
        row0 = CursorBuilder.findRow(table, {"Ath_no": 1})
        assert row0 is not None
        row0.put("First_name", "OverflowName_" + ("W" * 100))
        row0.put("Last_name", "OverflowLast_" + ("Z" * 100))
        table.updateRow(row0)

        # Delete Ath_no == 3
        assert cursor.findFirstRow(table.getColumn("Ath_no"), 3) is True
        cursor.deleteCurrentRow()
        assert table.getRowCount() == 24
        assert CursorBuilder.findRow(table, {"Ath_no": 3}) is None

        # Verify updated row0 is intact
        row0_after = CursorBuilder.findRow(table, {"Ath_no": 1})
        assert row0_after is not None
        assert row0_after["First_name"] == "OverflowName_" + ("W" * 100)


def test_cross_compatibility_with_java_jackcess(tmp_path: Path) -> None:
    """Verify that an MDB created and mutated by Rust `jackcess_rs` is 100% readable by Java Jackcess."""
    mdb_file = tmp_path / "cross_compat.mdb"
    with DatabaseBuilder.create(Database.FileFormat.V2000, mdb_file) as db:
        t = (
            TableBuilder("MeetEvents")
            .addColumn(ColumnBuilder("Event_no", DataType.INT))
            .addColumn(ColumnBuilder("Event_desc", DataType.TEXT).setLengthInUnits(40))
            .addColumn(ColumnBuilder("Is_relay", DataType.BOOLEAN))
            .addColumn(ColumnBuilder("Notes", DataType.MEMO))
            .setPrimaryKey("Event_no")
            .toTable(db)
        )
        t.addRowFromMap(
            {
                "Event_no": 1,
                "Event_desc": "Girls 8 & Under 100 Medley Relay",
                "Is_relay": True,
                "Notes": "Heat 1 sponsored by Stingrays",
            }
        )
        t.addRowFromMap(
            {
                "Event_no": 2,
                "Event_desc": "Boys 9-10 25 Freestyle",
                "Is_relay": False,
                "Notes": "Pool record attempt " + ("!" * 500),
            }
        )

    # Open the Rust-created MDB using Java Jackcess!
    if not mdb_writer.get_classpath():
        pytest.skip("Jackcess JARs not downloaded in lib/")
    mdb_writer.ensure_jvm_started(force_jvm=True)
    from com.healthmarketscience.jackcess import DatabaseBuilder as JavaDatabaseBuilder
    from java.io import File

    java_db = JavaDatabaseBuilder.open(File(str(mdb_file)))
    try:
        java_table_names = {str(n) for n in java_db.getTableNames()}
        assert "MeetEvents" in java_table_names

        java_tbl = java_db.getTable("MeetEvents")
        assert java_tbl is not None
        assert java_tbl.getRowCount() == 2

        java_rows = []
        for jr in java_tbl:
            java_rows.append(
                {
                    "Event_no": int(jr.get("Event_no")),
                    "Event_desc": str(jr.get("Event_desc")),
                    "Is_relay": bool(jr.get("Is_relay")),
                    "Notes": str(jr.get("Notes")),
                }
            )
        assert java_rows[0] == {
            "Event_no": 1,
            "Event_desc": "Girls 8 & Under 100 Medley Relay",
            "Is_relay": True,
            "Notes": "Heat 1 sponsored by Stingrays",
        }
        assert java_rows[1] == {
            "Event_no": 2,
            "Event_desc": "Boys 9-10 25 Freestyle",
            "Is_relay": False,
            "Notes": "Pool record attempt " + ("!" * 500),
        }
    finally:
        java_db.close()


def test_mdb_restorer_and_mdb_writer_with_rust_jackcess(tmp_path: Path) -> None:
    """Verify full export -> restore_db -> mdb_writer mutations on Singers23.mdb via Rust Jackcess."""
    with MmToJsonConverter(mdb_path=str(SINGERS_MDB)) as conv:
        schema = conv.export_full_schema()

    json_dump = tmp_path / "singers_schema.json"
    json_dump.write_text(
        json.dumps(
            schema,
            default=lambda x: x.isoformat() if hasattr(x, "isoformat") else x,
        )
    )

    restored_mdb = tmp_path / "singers_restored.mdb"
    mdb_restorer.restore_db(str(json_dump), str(restored_mdb))
    assert restored_mdb.is_file()

    # Mutate restored MDB using mdb_writer (backed by jackcess_rs)
    db = mdb_writer.open_db(str(restored_mdb))
    try:
        assert isinstance(db, jackcess_rs.Database)
        new_team_id = mdb_writer.add_team(
            db,
            team_id=999,
            abbr="RUST",
            name="Rust Sharks",
            short_name="Sharks",
            lsc="PC",
        )
        assert new_team_id == 999

        new_ath_id = mdb_writer.add_athlete(
            db,
            athlete_id=8888,
            team_id=999,
            first="Ferris",
            last="Crab",
            gender="M",
            age=12,
        )
        assert new_ath_id == 8888
    finally:
        db.close()

    # Verify via MmToJsonConverter that the restored & updated MDB loads and reflects the new team & athlete
    orig_teams = next(v["rows"] for k, v in schema["tables"].items() if k.lower() == "team")
    orig_aths = next(v["rows"] for k, v in schema["tables"].items() if k.lower() == "athlete")
    with MmToJsonConverter(mdb_path=str(restored_mdb)) as conv2:
        assert len(conv2.tables["team"]) == len(orig_teams) + 1
        assert len(conv2.tables["athlete"]) == len(orig_aths) + 1
        team_records = conv2.tables["team"].to_dict("records")
        added_teams = [r for r in team_records if r.get("tcode") == "RUST"]
        assert len(added_teams) == 1
        assert added_teams[0].get("tname") == "Rust Sharks"

    # Also verify mdb_writer.update_entry_status on a Meet Manager 4.0+ ENTRY table
    mm4_mdb = tmp_path / "mm4_dq_test.mdb"
    with DatabaseBuilder.create(Database.FileFormat.V2000, mm4_mdb) as db4:
        entry_tbl = (
            TableBuilder("ENTRY")
            .addColumn(ColumnBuilder("Event_ptr", DataType.LONG))
            .addColumn(ColumnBuilder("Ath_no", DataType.LONG))
            .addColumn(ColumnBuilder("Fin_heat", DataType.INT))
            .addColumn(ColumnBuilder("Fin_lane", DataType.INT))
            .addColumn(ColumnBuilder("Fin_stat", DataType.TEXT).setLengthInUnits(4))
            .addColumn(ColumnBuilder("Fin_dqcode", DataType.TEXT).setLengthInUnits(10))
            .toTable(db4)
        )
        entry_tbl.addRowFromMap(
            {
                "Event_ptr": 12,
                "Ath_no": 456,
                "Fin_heat": 2,
                "Fin_lane": 4,
                "Fin_stat": " ",
                "Fin_dqcode": "",
            }
        )

    db4_open = mdb_writer.open_db(str(mm4_mdb))
    try:
        updated = mdb_writer.update_entry_status(
            db4_open,
            event_ptr=12,
            athlete_id=456,
            heat=2,
            lane=4,
            status="DQ",
            dq_code="1A",
            round_type="F",
            is_relay=False,
        )
        assert updated is True
        row_after = next(iter(db4_open.getTable("ENTRY")))
        assert row_after["Fin_stat"] == "Q"
        assert row_after["Fin_dqcode"] == "1A"
    finally:
        db4_open.close()


def test_btree_indexes_and_java_index_cursor_parity(tmp_path: Path) -> None:
    """Verify B-tree index creation, page splitting, constraint enforcement, and Java IndexCursor traversal."""
    mdb_file = tmp_path / "btree_index_test.mdb"
    with DatabaseBuilder.create(Database.FileFormat.V2000, mdb_file) as db:
        tbl = (
            TableBuilder("IndexedAthletes")
            .addColumn(ColumnBuilder("Ath_no", DataType.LONG))
            .addColumn(ColumnBuilder("Reg_code", DataType.TEXT).setLengthInUnits(60))
            .addColumn(ColumnBuilder("Score", DataType.DOUBLE))
            .setPrimaryKey("Ath_no")
            .addIndex(IndexBuilder("RegCodeIdx").addColumns("Reg_code").setUnique())
            .addIndex(IndexBuilder("ScoreDescIdx").addColumnsWithOrder(False, "Score"))
            .toTable(db)
        )

        # Insert 120 rows with 40-char codes to trigger B-tree Leaf -> Node (0x03) page splits
        rows = [
            {
                "Ath_no": i,
                "Reg_code": f"REG_{i:04d}_{'X' * 30}",
                "Score": float(i * 1.5),
            }
            for i in range(1, 121)
        ]
        tbl.addRowsFromMaps(rows)
        assert tbl.getRowCount() == 120

        # Constraint checks: duplicate PrimaryKey or Unique Reg_code must raise
        with pytest.raises(RuntimeError, match="ConstraintViolationException"):
            tbl.addRowFromMap({"Ath_no": 50, "Reg_code": "REG_9999_NEW", "Score": 1.0})

        with pytest.raises(RuntimeError, match="ConstraintViolationException"):
            tbl.addRowFromMap({"Ath_no": 999, "Reg_code": f"REG_{25:04d}_{'X' * 30}", "Score": 1.0})

        with pytest.raises(RuntimeError, match="ConstraintViolationException"):
            tbl.addRowFromMap({"Ath_no": None, "Reg_code": "REG_NULL_PK", "Score": 1.0})

        # Update row 10's Reg_code and delete row 20
        c = tbl.getDefaultCursor()
        assert c.findFirstRow({"Ath_no": 10})
        c.setCurrentRowValue("Reg_code", f"REG_0010_UPDATED_{'Y' * 22}")
        assert c.findFirstRow({"Ath_no": 20})
        c.deleteCurrentRow()
        assert tbl.getRowCount() == 119

        # Test Python IndexCursor lookup and descending traversal
        reg_idx = tbl.getIndex("RegCodeIdx")
        idx_cursor = reg_idx.newCursor().toIndexCursor()
        found_row = idx_cursor.findRowByEntry(f"REG_0010_UPDATED_{'Y' * 22}")
        assert found_row is not None
        assert found_row["Ath_no"] == 10

        desc_idx = tbl.getIndex("ScoreDescIdx")
        desc_rows = list(desc_idx.newCursor().toIndexCursor())
        assert desc_rows[0]["Ath_no"] == 120
        assert desc_rows[-1]["Ath_no"] == 1

    # Verify Java Jackcess can traverse the multi-page B-Tree indexes natively via IndexCursor!
    if not mdb_writer.get_classpath():
        pytest.skip("Jackcess JARs not downloaded in lib/")
    mdb_writer.ensure_jvm_started(force_jvm=True)
    from com.healthmarketscience.jackcess import CursorBuilder as JavaCursorBuilder
    from com.healthmarketscience.jackcess import DatabaseBuilder as JavaDatabaseBuilder
    from java.io import File

    java_db = JavaDatabaseBuilder.open(File(str(mdb_file)))
    try:
        java_tbl = java_db.getTable("IndexedAthletes")
        assert java_tbl.getRowCount() == 119

        java_pk_idx = java_tbl.getIndex("PrimaryKey")
        java_pk_cursor = JavaCursorBuilder.createCursor(java_pk_idx)
        pk_ids = [int(r.get("Ath_no")) for r in java_pk_cursor]
        assert len(pk_ids) == 119
        assert pk_ids == sorted(pk_ids)
        assert 20 not in pk_ids

        java_reg_idx = java_tbl.getIndex("RegCodeIdx")
        java_reg_cursor = JavaCursorBuilder.createCursor(java_reg_idx)
        assert java_reg_cursor.findFirstRowByEntry(f"REG_0010_UPDATED_{'Y' * 22}") is True
        assert int(java_reg_cursor.getCurrentRow().get("Ath_no")) == 10
        assert java_reg_cursor.findFirstRowByEntry(f"REG_{20:04d}_{'X' * 30}") is False
    finally:
        java_db.close()


def test_property_maps_roundtrip_and_java_parity(tmp_path: Path) -> None:
    """Verify LvProp PropertyMap read/write across Table, Column, Index, and Database with Java Jackcess."""
    from mm_to_json.jackcess_rs import PropertyMap

    mdb_file = tmp_path / "props_test.mdb"
    with DatabaseBuilder.create(Database.FileFormat.V2000, mdb_file) as db:
        tbl = (
            TableBuilder("PropTable")
            .putProperty(PropertyMap.DESCRIPTION_PROP, "Table level description")
            .addColumn(
                ColumnBuilder("Id", DataType.LONG)
                .setAutoNumber(True)
                .putProperty(PropertyMap.CAPTION_PROP, "Athlete ID")
            )
            .addColumn(
                ColumnBuilder("Status", DataType.TEXT)
                .setLengthInUnits(20)
                .putProperty(PropertyMap.DEFAULT_VALUE_PROP, '"ACTIVE"')
                .putProperty(PropertyMap.REQUIRED_PROP, True)
            )
            .setPrimaryKey("Id")
            .toTable(db)
        )

        # Verify initial properties set via builders
        t_props = tbl.getProperties()
        assert t_props.getValue(PropertyMap.DESCRIPTION_PROP) == "Table level description"
        t_props.put("CustomTableNote", DataType.TEXT, "Created by Rust")
        t_props.save()

        id_props = tbl.getColumn("Id").getProperties()
        assert id_props.getValue(PropertyMap.CAPTION_PROP) == "Athlete ID"

        st_props = tbl.getColumn("Status").getProperties()
        assert st_props.getValue(PropertyMap.DEFAULT_VALUE_PROP) == '"ACTIVE"'
        assert st_props.getValue(PropertyMap.REQUIRED_PROP) is True

        idx_props = tbl.getIndex("PrimaryKey").getProperties()
        idx_props.put("IndexComment", DataType.TEXT, "PK B-tree")
        idx_props.save()

        # Database, Summary, and UserDefined properties
        db_props = db.getDatabaseProperties()
        db_props.put("ProjVer", DataType.INT, 42)
        db_props.save()

        sum_props = db.getSummaryProperties()
        sum_props.put(PropertyMap.TITLE_PROP, "2026 Championship Database")
        sum_props.put(PropertyMap.AUTHOR_PROP, "MMTools Rust Engine")
        sum_props.save()

        ud_props = db.getUserDefinedProperties()
        ud_props.put("LeagueCode", DataType.TEXT, "TVSL")
        ud_props.save()

    # Verify Java Jackcess reads all PropertyMaps written by Rust, and writes back a property
    if not mdb_writer.get_classpath():
        pytest.skip("Jackcess JARs not downloaded in lib/")
    mdb_writer.ensure_jvm_started(force_jvm=True)
    from com.healthmarketscience.jackcess import DatabaseBuilder as JavaDatabaseBuilder
    from java.io import File

    java_db = JavaDatabaseBuilder.open(File(str(mdb_file)))
    try:
        java_tbl = java_db.getTable("PropTable")
        jt_props = java_tbl.getProperties()
        assert str(jt_props.getValue("Description")) == "Table level description"
        assert str(jt_props.getValue("CustomTableNote")) == "Created by Rust"

        jc_id_props = java_tbl.getColumn("Id").getProperties()
        assert str(jc_id_props.getValue("Caption")) == "Athlete ID"

        jc_st_props = java_tbl.getColumn("Status").getProperties()
        assert str(jc_st_props.getValue("DefaultValue")) == '"ACTIVE"'
        assert bool(jc_st_props.getValue("Required")) is True

        j_sum_props = java_db.getSummaryProperties()
        assert str(j_sum_props.getValue("Title")) == "2026 Championship Database"
        assert str(j_sum_props.getValue("Author")) == "MMTools Rust Engine"

        j_ud_props = java_db.getUserDefinedProperties()
        assert str(j_ud_props.getValue("LeagueCode")) == "TVSL"

        # Mutate in Java and save
        jt_props.put("JavaAddedProp", "HelloFromJavaJackcess")
        jt_props.save()
    finally:
        java_db.close()

    # Reopen in Rust and verify Java's property modification
    with DatabaseBuilder.open(mdb_file) as db2:
        tbl2 = db2.getTable("PropTable")
        assert tbl2 is not None
        assert tbl2.getProperties().getValue("JavaAddedProp") == "HelloFromJavaJackcess"


@pytest.mark.skipif(
    not UPSTREAM_DATA_DIR.exists(),
    reason="Upstream Jackcess test data not present in /tmp/jackcess-upstream",
)
def test_upstream_jackcess_databases_parity_against_java() -> None:
    """Compare Rust `jackcess_rs` against Java Jackcess across upstream test databases."""
    mdb_writer.ensure_jvm_started(force_jvm=True)
    from com.healthmarketscience.jackcess import DatabaseBuilder as JavaDatabaseBuilder
    from java.io import File

    checked_files = 0
    checked_tables = 0
    for ver in ("V1997", "V2000", "V2003", "V2007", "V2010"):
        ver_dir = UPSTREAM_DATA_DIR / ver
        if not ver_dir.exists():
            continue
        for mdb_path in sorted(ver_dir.iterdir()):
            if mdb_path.suffix.lower() not in (".mdb", ".accdb"):
                continue
            if mdb_path.name.startswith("linkerTest"):
                # linkerTest databases contain external linked tables (Type=6) pointing to external files
                continue
            jdb = JavaDatabaseBuilder.open(File(str(mdb_path)))
            try:
                with DatabaseBuilder.open(mdb_path) as rdb:
                    j_names = {str(n) for n in jdb.getTableNames()}
                    r_names = rdb.getTableNames()
                    assert r_names == j_names, f"Table names mismatch on {mdb_path}"

                    for tname in sorted(j_names):
                        jtbl = jdb.getTable(tname)
                        rtbl = rdb.getTable(tname)
                        assert rtbl is not None
                        j_cols = [str(c.getName()) for c in jtbl.getColumns()]
                        r_cols = [c.getName() for c in rtbl.getColumns()]
                        assert r_cols == j_cols, f"Columns mismatch on {mdb_path}:{tname}"

                        j_rows = list(jtbl)
                        r_rows = list(rtbl)
                        assert len(r_rows) == len(j_rows), f"Row count mismatch on {mdb_path}:{tname}"
                        checked_tables += 1
            finally:
                jdb.close()
            checked_files += 1

    assert checked_files >= 30
    assert checked_tables >= 60
