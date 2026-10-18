"""Standalone Python package `jackcess_rs`: pure-Rust drop-in replacement for `com.healthmarketscience.jackcess`.

Re-exports the complete Jackcess API (`Database`, `DatabaseBuilder`, `Table`, `TableBuilder`,
`Column`, `ColumnBuilder`, `Index`, `IndexBuilder`, `IndexColumn`, `Cursor`, `CursorBuilder`,
`DataType`, `FileFormat`, `Property`, `PropertyMap`, `Row`, `RowId`, `JackcessDateTime`)
backed by the Rust `jackcess_rs` engine with zero JVM or JPype dependencies.
"""

from __future__ import annotations

from mm_to_json.jackcess_rs import (
    Column,
    ColumnBuilder,
    Cursor,
    CursorBuilder,
    Database,
    DatabaseBuilder,
    DataType,
    FileFormat,
    Index,
    IndexBuilder,
    IndexColumn,
    JackcessDateTime,
    Property,
    PropertyMap,
    Row,
    RowId,
    Table,
    TableBuilder,
)

__all__ = [
    "Column",
    "ColumnBuilder",
    "Cursor",
    "CursorBuilder",
    "DataType",
    "Database",
    "DatabaseBuilder",
    "FileFormat",
    "Index",
    "IndexBuilder",
    "IndexColumn",
    "JackcessDateTime",
    "Property",
    "PropertyMap",
    "Row",
    "RowId",
    "Table",
    "TableBuilder",
]
