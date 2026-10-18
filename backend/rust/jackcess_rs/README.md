# `jackcess-rs` / `jackcess_rs`

A pure-Rust reader and writer for Microsoft Access Jet 3 (`V1997`), Jet 4 (`V2000`/`V2003`), and ACE (`V2007`–`V2019`) `.mdb` and `.accdb` databases, with a drop-in Python API (`jackcess_rs`) matching `com.healthmarketscience.jackcess` — requiring **zero Java/JVM or JPype dependencies**.

## Features

- **Multi-Version Reading**: Reads Jet 3 (`V1997`, 2048-byte pages, Latin-1), Jet 4 (`V2000`/`V2003`, 4096-byte pages, UTF-16LE / compressed Unicode), and ACE (`V2007`–`V2019`) `.mdb` and `.accdb` databases.
- **Full Jet 4 (`V2000`) Database & Table Creation**:
  - `DatabaseBuilder.create(Database.FileFormat.V2000, path)` initializes a valid 24-page Jet 4 `.mdb` file with system catalog tables (`MSysObjects`, `MSysACEs`, `MSysQueries`, `MSysRelationships`).
  - `TableBuilder`, `ColumnBuilder`, and `IndexBuilder` create single- and multi-page TDEFs, UsageMaps (inline `0x00` and reference `0x01`), and `MSysObjects` catalog entries.
- **All Column Data Types & Long Value (`LVAL`) Chains**:
  - `BOOLEAN`, `BYTE`, `INT`, `LONG` (including `AutoNumber`), `MONEY`, `FLOAT`, `DOUBLE`, `SHORT_DATE_TIME`, `BINARY`, `TEXT`, `OLE`, `MEMO`, `GUID`, `NUMERIC`, `COMPLEX_TYPE`, `BIG_INT`.
  - Inline (`type 2`), single-page (`type 1`), and multi-page (`type 0`) `LVAL` chains for `MEMO` and `OLE` columns.
- **Row CRUD (`addRow`, `updateRow`, `deleteRow`, `Cursor`, `IndexCursor`)**:
  - In-place row updates and automatic overflow pointer (`0x4000`) page promotion when updated rows exceed page free space.
  - Row deletion (`0xC000`) with boundary preservation (`findRowEnd` parity with Java Jackcess).
- **User-Table B-Tree Index Maintenance**:
  - Byte-for-byte sortable key encoding across all column types (including `GeneralLegacyIndexCodes` collation for `TEXT` and descending byte inversion).
  - Entry prefix compression (`entryMask`) and automatic Leaf (`0x04`) $\to$ Node (`0x03`) B-tree page splitting with `childTailPageNumber` promotion.
  - Enforces `unique`, `required`, and `ignore_nulls` index constraints (`ConstraintViolationException`), verified against Java Jackcess `IndexCursor`.
- **`PropertyMap` (`LvProp` `MR2\0` / `KKD\0`) Support**:
  - Reads and writes `table.getProperties()`, `col.getProperties()`, `index.getProperties()`, `db.getDatabaseProperties()`, `db.getSummaryProperties()`, and `db.getUserDefinedProperties()`.

## Python Usage

```python
from jackcess_rs import (
    ColumnBuilder,
    CursorBuilder,
    Database,
    DatabaseBuilder,
    DataType,
    IndexBuilder,
    PropertyMap,
    TableBuilder,
)

with DatabaseBuilder.create(Database.FileFormat.V2000, "example.mdb") as db:
    table = (
        TableBuilder("Athletes")
        .putProperty(PropertyMap.DESCRIPTION_PROP, "Registered swimmers")
        .addColumn(ColumnBuilder("Ath_no", DataType.LONG).setAutoNumber(True))
        .addColumn(ColumnBuilder("Reg_code", DataType.TEXT).setLengthInUnits(30))
        .addColumn(ColumnBuilder("First_name", DataType.TEXT).setLengthInUnits(30))
        .setPrimaryKey("Ath_no")
        .addIndex(IndexBuilder("RegCodeIdx").addColumns("Reg_code").setUnique())
        .toTable(db)
    )
    table.addRowFromMap({"Reg_code": "PC-001", "First_name": "Katie"})

    cursor = table.getIndex("RegCodeIdx").newCursor().toIndexCursor()
    row = cursor.findRowByEntry("PC-001")
```

## License & Attribution

Licensed under the Apache License, Version 2.0. Binary format specifications and collation tables are derived from [Jackcess](https://github.com/jahlborn/jackcess) (`com.healthmarketscience.jackcess`, Apache-2.0).
