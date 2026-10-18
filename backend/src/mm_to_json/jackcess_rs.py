"""Pure-Rust-backed drop-in Python replacement for `com.healthmarketscience.jackcess`.

Provides the Jackcess API (`Database`, `DatabaseBuilder`, `Table`, `TableBuilder`,
`Column`, `ColumnBuilder`, `Index`, `IndexBuilder`, `Cursor`, `CursorBuilder`,
`DataType`, `Row`, `RowId`) backed by `mm_core_rs` (`jackcess.rs` & `mdb.rs`)
with zero JVM or JPype dependencies.
"""

from __future__ import annotations

import base64
import datetime
from collections.abc import Iterable, Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

from .rust_bridge import rust_jackcess_exec


class JackcessDateTime(datetime.datetime):
    """`datetime.datetime` subclass that also provides Java `java.util.Date.getTime()`."""

    def getTime(self) -> float:
        """Return milliseconds since the Unix epoch (matching `java.util.Date.getTime()`)."""
        return self.timestamp() * 1000.0


class _DataTypeItem:
    """Represents a single Jackcess `DataType` enum constant."""

    def __init__(self, name_str: str, code: int, variable_length: bool, default_size: int) -> None:
        self._name = name_str
        self._code = code
        self._variable_length = variable_length
        self._default_size = default_size

    def name(self) -> str:
        """Return the Java enum name string (e.g. `'TEXT'`, `'LONG'`)."""
        return self._name

    def getValue(self) -> int:
        """Return the raw Jet column type byte code."""
        return self._code

    def isVariableLength(self) -> bool:
        """Return True if this data type is variable length."""
        return self._variable_length

    def getDefaultSize(self) -> int:
        """Return the default byte length of this column type."""
        return self._default_size

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"DataType.{self._name}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _DataTypeItem):
            return self._code == other._code
        if isinstance(other, str):
            return self._name.upper() == other.upper()
        return False

    def __hash__(self) -> int:
        return hash(self._code)


class _DataTypeMeta(type):
    """Metaclass allowing `DataType['TEXT']` and `DataType.valueOf('TEXT')`."""

    def __getitem__(cls, key: str) -> _DataTypeItem:
        return DataType.valueOf(key)


class DataType(metaclass=_DataTypeMeta):
    """Jackcess `DataType` enum constants and lookup utilities."""

    BOOLEAN = _DataTypeItem("BOOLEAN", 0x01, False, 1)
    BYTE = _DataTypeItem("BYTE", 0x02, False, 1)
    INT = _DataTypeItem("INT", 0x03, False, 2)
    LONG = _DataTypeItem("LONG", 0x04, False, 4)
    MONEY = _DataTypeItem("MONEY", 0x05, False, 8)
    FLOAT = _DataTypeItem("FLOAT", 0x06, False, 4)
    DOUBLE = _DataTypeItem("DOUBLE", 0x07, False, 8)
    SHORT_DATE_TIME = _DataTypeItem("SHORT_DATE_TIME", 0x08, False, 8)
    BINARY = _DataTypeItem("BINARY", 0x09, True, 255)
    TEXT = _DataTypeItem("TEXT", 0x0A, True, 50)
    OLE = _DataTypeItem("OLE", 0x0B, True, 0)
    MEMO = _DataTypeItem("MEMO", 0x0C, True, 0)
    UNKNOWN_0D = _DataTypeItem("UNKNOWN_0D", 0x0D, True, 0)
    GUID = _DataTypeItem("GUID", 0x0F, False, 16)
    NUMERIC = _DataTypeItem("NUMERIC", 0x10, False, 17)
    UNKNOWN_11 = _DataTypeItem("UNKNOWN_11", 0x11, True, 0)
    COMPLEX_TYPE = _DataTypeItem("COMPLEX_TYPE", 0x12, False, 4)
    BIG_INT = _DataTypeItem("BIG_INT", 0x13, False, 8)
    EXT_DATE_TIME = _DataTypeItem("EXT_DATE_TIME", 0x14, False, 42)
    UNSUPPORTED_FIXEDLEN = _DataTypeItem("UNSUPPORTED_FIXEDLEN", 0xFE, False, 0)
    UNSUPPORTED_VARLEN = _DataTypeItem("UNSUPPORTED_VARLEN", 0xFF, True, 0)

    _BY_NAME: dict[str, _DataTypeItem] = {
        "BOOLEAN": BOOLEAN,
        "BIT": BOOLEAN,
        "BYTE": BYTE,
        "INT": INT,
        "SHORT": INT,
        "LONG": LONG,
        "INTEGER": LONG,
        "MONEY": MONEY,
        "CURRENCY": MONEY,
        "FLOAT": FLOAT,
        "SINGLE": FLOAT,
        "DOUBLE": DOUBLE,
        "SHORT_DATE_TIME": SHORT_DATE_TIME,
        "DATETIME": SHORT_DATE_TIME,
        "BINARY": BINARY,
        "TEXT": TEXT,
        "OLE": OLE,
        "MEMO": MEMO,
        "UNKNOWN_0D": UNKNOWN_0D,
        "GUID": GUID,
        "NUMERIC": NUMERIC,
        "UNKNOWN_11": UNKNOWN_11,
        "COMPLEX_TYPE": COMPLEX_TYPE,
        "BIG_INT": BIG_INT,
        "EXT_DATE_TIME": EXT_DATE_TIME,
        "UNSUPPORTED_FIXEDLEN": UNSUPPORTED_FIXEDLEN,
        "UNSUPPORTED_VARLEN": UNSUPPORTED_VARLEN,
        "UNKNOWN": UNSUPPORTED_VARLEN,
    }

    @classmethod
    def valueOf(cls, name: str | _DataTypeItem) -> _DataTypeItem:
        """Resolve a `DataType` by name or instance."""
        if isinstance(name, _DataTypeItem):
            return name
        key = str(name).strip().upper()
        if key in cls._BY_NAME:
            return cls._BY_NAME[key]
        raise ValueError(f"Unknown Jackcess DataType: {name}")


class FileFormat:
    """Jackcess `Database.FileFormat` constants."""

    V1997 = "V1997"
    V2000 = "V2000"
    V2003 = "V2003"
    V2007 = "V2007"
    V2010 = "V2010"
    V2016 = "V2016"
    V2019 = "V2019"


class RowId:
    """Jackcess `RowId` identifying a physical `(page_number, row_number)` tuple."""

    def __init__(self, page_number: int, row_number: int) -> None:
        self._page_number = int(page_number)
        self._row_number = int(row_number)

    def getPageNumber(self) -> int:
        """Return the physical data page number."""
        return self._page_number

    def getRowNumber(self) -> int:
        """Return the row index on the physical data page."""
        return self._row_number

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RowId):
            return (self._page_number, self._row_number) == (other._page_number, other._row_number)
        return False

    def __hash__(self) -> int:
        return hash((self._page_number, self._row_number))

    def __repr__(self) -> str:
        return f"{self._page_number}:{self._row_number}"


class Row(dict[str, Any]):
    """Jackcess `Row` mapping column names to values with Java `Map`/`Row` methods."""

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        row_id: RowId | None = None,
    ) -> None:
        super().__init__(data or {})
        self._row_id = row_id or RowId(0, 0)

    def getId(self) -> RowId:
        """Return the physical `RowId` of this row."""
        return self._row_id

    def _resolve_key(self, key: Any) -> str:
        k_str = key.getName() if hasattr(key, "getName") else str(key)
        if super().__contains__(k_str):
            return k_str
        k_low = k_str.lower()
        for existing in self.keys():
            if existing.lower() == k_low:
                return existing
        return k_str

    def get(self, key: Any, default: Any = None) -> Any:
        """Return the value for `key` (case-insensitive fallback)."""
        rk = self._resolve_key(key)
        return super().get(rk, default)

    def put(self, key: Any, value: Any) -> Any:
        """Set `key` to `value` and return the previous value (Java `Map.put` API)."""
        rk = self._resolve_key(key)
        old = super().get(rk)
        self[rk] = value
        return old

    def getString(self, key: Any) -> str | None:
        """Return column value as `str` or `None`."""
        val = self.get(key)
        return None if val is None else str(val)

    def getInt(self, key: Any) -> int | None:
        """Return column value as `int` (`LONG`) or `None`."""
        val = self.get(key)
        return None if val is None else int(val)

    def getShort(self, key: Any) -> int | None:
        """Return column value as `int` (`INT`) or `None`."""
        val = self.get(key)
        return None if val is None else int(val)

    def getByte(self, key: Any) -> int | None:
        """Return column value as `int` (`BYTE`) or `None`."""
        val = self.get(key)
        return None if val is None else int(val)

    def getDouble(self, key: Any) -> float | None:
        """Return column value as `float` or `None`."""
        val = self.get(key)
        return None if val is None else float(val)

    def getBoolean(self, key: Any) -> bool | None:
        """Return column value as `bool` or `None`."""
        val = self.get(key)
        return None if val is None else bool(val)

    def getBytes(self, key: Any) -> bytes | None:
        """Return column value as `bytes` or `None`."""
        val = self.get(key)
        if val is None:
            return None
        if isinstance(val, bytes):
            return val
        if isinstance(val, bytearray):
            return bytes(val)
        if isinstance(val, str):
            return base64.b64decode(val)
        return bytes(val)


class Column:
    """Jackcess `Column` metadata descriptor."""

    def __init__(
        self,
        name: str,
        data_type: _DataTypeItem | str,
        length: int = 0,
        auto_number: bool = False,
        variable_length: bool | None = None,
        precision: int = 0,
        scale: int = 0,
        col_index: int = 0,
        col_id: int = 0,
    ) -> None:
        self._name = name
        self._type = DataType.valueOf(data_type)
        self._length = int(length) if length else self._type.getDefaultSize()
        self._auto_number = bool(auto_number)
        self._variable_length = self._type.isVariableLength() if variable_length is None else bool(variable_length)
        self._precision = int(precision)
        self._scale = int(scale)
        self._col_index = int(col_index)
        self._col_id = int(col_id)

    def getName(self) -> str:
        """Return the column name."""
        return self._name

    def getType(self) -> _DataTypeItem:
        """Return the column `DataType`."""
        return self._type

    def getLength(self) -> int:
        """Return the column byte length."""
        return self._length

    def getLengthInUnits(self) -> int:
        """Return the column length in character units (for TEXT, `length // 2`)."""
        if self._type == DataType.TEXT:
            return max(1, self._length // 2)
        return self._length

    def isAutoNumber(self) -> bool:
        """Return True if this column is an AutoNumber column."""
        return self._auto_number

    def isVariableLength(self) -> bool:
        """Return True if this column is stored as variable length."""
        return self._variable_length

    def getPrecision(self) -> int:
        """Return numeric precision."""
        return self._precision

    def getScale(self) -> int:
        """Return numeric scale."""
        return self._scale

    def getColumnIndex(self) -> int:
        """Return the 0-based column index in the table."""
        return self._col_index

    def to_dict(self, idx: int = 0) -> dict[str, Any]:
        """Serialize column definition for Rust `jackcess.rs`."""
        return {
            "name": self._name,
            "type": self._type.name(),
            "col_type": self._type.getValue(),
            "col_id": self._col_id or idx,
            "col_index": self._col_index or idx,
            "var_col_num": 0,
            "fixed_offset": 0,
            "length": self._length,
            "variable": self._variable_length,
            "auto_number": self._auto_number,
            "precision": self._precision,
            "scale": self._scale,
        }


class ColumnBuilder:
    """Jackcess `ColumnBuilder` for constructing `Column` definitions."""

    def __init__(self, name: str, data_type: _DataTypeItem | str | None = None) -> None:
        self._name = name
        self._type: _DataTypeItem = DataType.valueOf(data_type) if data_type is not None else DataType.TEXT
        self._length: int | None = None
        self._auto_number: bool = False
        self._precision: int = 18
        self._scale: int = 0

    def setType(self, data_type: _DataTypeItem | str) -> ColumnBuilder:
        """Set the column `DataType`."""
        self._type = DataType.valueOf(data_type)
        return self

    def setLength(self, length: int) -> ColumnBuilder:
        """Set the exact byte length of the column."""
        self._length = int(length)
        return self

    def setLengthInUnits(self, units: int) -> ColumnBuilder:
        """Set the length in character units (multiplied by 2 for Jet4 UTF-16 TEXT)."""
        if self._type == DataType.TEXT:
            self._length = int(units) * 2
        else:
            self._length = int(units)
        return self

    def setMaxLength(self) -> ColumnBuilder:
        """Set the column to the maximum supported length for its type."""
        if self._type == DataType.TEXT:
            self._length = 510
        elif self._type == DataType.BINARY:
            self._length = 510
        return self

    def setAutoNumber(self, auto_num: bool) -> ColumnBuilder:
        """Configure whether the column is an AutoNumber column."""
        self._auto_number = bool(auto_num)
        return self

    def setPrecision(self, precision: int) -> ColumnBuilder:
        """Set numeric precision."""
        self._precision = int(precision)
        return self

    def setScale(self, scale: int) -> ColumnBuilder:
        """Set numeric scale."""
        self._scale = int(scale)
        return self

    def setCompressedUnicode(self, _compressed: bool) -> ColumnBuilder:
        """No-op for compatibility with Jackcess `setCompressedUnicode`."""
        return self

    def toColumn(self) -> Column:
        """Build and return the `Column`."""
        length = self._length if self._length is not None else self._type.getDefaultSize()
        return Column(
            name=self._name,
            data_type=self._type,
            length=length,
            auto_number=self._auto_number,
            variable_length=self._type.isVariableLength(),
            precision=self._precision,
            scale=self._scale,
        )


class IndexColumn:
    """Represents a column reference inside a Jackcess `Index`."""

    def __init__(self, name: str, ascending: bool = True) -> None:
        self._name = name
        self._ascending = bool(ascending)

    def getName(self) -> str:
        """Return the column name."""
        return self._name

    def isAscending(self) -> bool:
        """Return True if sorted ascending."""
        return self._ascending


class Index:
    """Jackcess `Index` metadata descriptor."""

    def __init__(
        self,
        name: str,
        columns: Iterable[IndexColumn | dict[str, Any] | str],
        unique: bool = False,
        primary_key: bool = False,
        ignore_nulls: bool = False,
        required: bool = False,
    ) -> None:
        self._name = name
        self._columns: list[IndexColumn] = []
        for c in columns:
            if isinstance(c, IndexColumn):
                self._columns.append(c)
            elif isinstance(c, dict):
                self._columns.append(IndexColumn(str(c.get("name", "")), bool(c.get("ascending", True))))
            else:
                self._columns.append(IndexColumn(str(c), True))
        self._primary_key = bool(primary_key) or name == IndexBuilder.PRIMARY_KEY_NAME
        self._unique = bool(unique) or self._primary_key
        self._ignore_nulls = bool(ignore_nulls)
        self._required = bool(required)

    def getName(self) -> str:
        """Return the index name."""
        return self._name

    def isUnique(self) -> bool:
        """Return True if the index enforces uniqueness."""
        return self._unique

    def isPrimaryKey(self) -> bool:
        """Return True if the index is the primary key."""
        return self._primary_key

    def isIgnoreNulls(self) -> bool:
        """Return True if the index ignores nulls."""
        return self._ignore_nulls

    def isRequired(self) -> bool:
        """Return True if the index requires non-null values."""
        return self._required

    def getColumns(self) -> list[IndexColumn]:
        """Return the list of `IndexColumn` descriptors."""
        return list(self._columns)

    def to_dict(self) -> dict[str, Any]:
        """Serialize index definition for Rust `jackcess.rs`."""
        return {
            "name": self._name,
            "unique": self._unique,
            "columns": [c.getName() for c in self._columns],
        }


class IndexBuilder:
    """Jackcess `IndexBuilder` for constructing `Index` definitions."""

    PRIMARY_KEY_NAME = "PrimaryKey"

    def __init__(self, name: str) -> None:
        self._name = name
        self._columns: list[IndexColumn] = []
        self._unique = False
        self._primary_key = name == self.PRIMARY_KEY_NAME
        self._ignore_nulls = False
        self._required = False

    def addColumns(self, *names: str | list[str] | tuple[str, ...]) -> IndexBuilder:
        """Add ascending columns to this index."""
        for n in names:
            if isinstance(n, (list, tuple)):
                for sub in n:
                    self._columns.append(IndexColumn(str(sub), True))
            else:
                self._columns.append(IndexColumn(str(n), True))
        return self

    def addColumnsWithOrder(self, ascending: bool, *names: str) -> IndexBuilder:
        """Add columns with explicit sort order to this index."""
        for n in names:
            self._columns.append(IndexColumn(str(n), ascending))
        return self

    def setPrimaryKey(self) -> IndexBuilder:
        """Mark this index as the primary key (and unique)."""
        self._primary_key = True
        self._unique = True
        return self

    def setUnique(self) -> IndexBuilder:
        """Mark this index as unique."""
        self._unique = True
        return self

    def setIgnoreNulls(self) -> IndexBuilder:
        """Mark this index as ignoring nulls."""
        self._ignore_nulls = True
        return self

    def setRequired(self) -> IndexBuilder:
        """Mark this index as required."""
        self._required = True
        return self

    def toIndex(self) -> Index:
        """Build and return the `Index`."""
        return Index(
            name=self._name,
            columns=self._columns,
            unique=self._unique,
            primary_key=self._primary_key,
            ignore_nulls=self._ignore_nulls,
            required=self._required,
        )


class Cursor:
    """Jackcess `Cursor` for navigating, searching, updating, and deleting table rows."""

    def __init__(self, table: Table) -> None:
        self._table = table
        self._pos = -1

    def reset(self) -> None:
        """Reset cursor before the first row."""
        self._pos = -1

    def beforeFirst(self) -> None:
        """Position cursor before the first row."""
        self._pos = -1

    def afterLast(self) -> None:
        """Position cursor after the last row."""
        self._pos = len(self._table._rows)

    def getNextRow(self) -> Row | None:
        """Advance to the next row and return it, or `None` if at the end."""
        self._pos += 1
        if 0 <= self._pos < len(self._table._rows):
            return self._table._rows[self._pos]
        return None

    def getPreviousRow(self) -> Row | None:
        """Move to the previous row and return it, or `None` if at the beginning."""
        if self._pos > len(self._table._rows):
            self._pos = len(self._table._rows)
        self._pos -= 1
        if 0 <= self._pos < len(self._table._rows):
            return self._table._rows[self._pos]
        return None

    def getCurrentRow(self) -> Row | None:
        """Return the row at the current cursor position."""
        if 0 <= self._pos < len(self._table._rows):
            return self._table._rows[self._pos]
        return None

    def getCurrentRowValue(self, column: Column | str) -> Any:
        """Return the value of `column` on the current row."""
        row = self.getCurrentRow()
        if row is None:
            return None
        col_name = column.getName() if isinstance(column, Column) else str(column)
        return row.get(col_name)

    def setCurrentRowValue(self, column: Column | str, value: Any) -> None:
        """Update a single column on the current row and persist to the database."""
        row = self.getCurrentRow()
        if row is None:
            raise RuntimeError("Cursor does not point to a valid row")
        col_name = column.getName() if isinstance(column, Column) else str(column)
        row.put(col_name, value)
        self._table.updateRow(row)

    def updateCurrentRow(self, *row_values: Any) -> None:
        """Update the current row with positional column values."""
        row = self.getCurrentRow()
        if row is None:
            raise RuntimeError("Cursor does not point to a valid row")
        cols = self._table.getColumns()
        for idx, val in enumerate(row_values):
            if idx < len(cols):
                row[cols[idx].getName()] = val
        self._table.updateRow(row)

    def deleteCurrentRow(self) -> None:
        """Delete the row at the current cursor position."""
        row = self.getCurrentRow()
        if row is None:
            raise RuntimeError("Cursor does not point to a valid row")
        self._table.deleteRow(row)
        self._pos -= 1

    def _matches(self, row: Row, criteria: dict[Any, Any]) -> bool:
        for k, expected in criteria.items():
            col_name = k.getName() if hasattr(k, "getName") else str(k)
            actual = row.get(col_name)
            if actual != expected:
                return False
        return True

    def findFirstRow(self, criteria_or_col: Any, value: Any = None) -> bool:
        """Find the first row matching `criteria_or_col` (map or `(Column, value)`)."""
        criteria = criteria_or_col if isinstance(criteria_or_col, dict) else {criteria_or_col: value}
        for idx, row in enumerate(self._table._rows):
            if self._matches(row, criteria):
                self._pos = idx
                return True
        return False

    def findNextRow(self, criteria_or_col: Any, value: Any = None) -> bool:
        """Find the next row after the current position matching `criteria_or_col`."""
        criteria = criteria_or_col if isinstance(criteria_or_col, dict) else {criteria_or_col: value}
        start = max(0, self._pos + 1)
        for idx in range(start, len(self._table._rows)):
            if self._matches(self._table._rows[idx], criteria):
                self._pos = idx
                return True
        return False

    def findRow(self, criteria: dict[Any, Any]) -> bool:
        """Alias for `findFirstRow(criteria)`."""
        return self.findFirstRow(criteria)

    def __iter__(self) -> Iterator[Row]:
        return iter(list(self._table._rows))


class CursorBuilder:
    """Jackcess `CursorBuilder` utility."""

    def __init__(self, table: Table) -> None:
        self._table = table

    def toCursor(self) -> Cursor:
        """Build a new `Cursor` for the table."""
        return Cursor(self._table)

    @staticmethod
    def createCursor(table: Table) -> Cursor:
        """Create a new `Cursor` for `table`."""
        return Cursor(table)

    @staticmethod
    def findRow(table: Table, criteria: dict[Any, Any]) -> Row | None:
        """Return the first `Row` in `table` matching `criteria`, or `None`."""
        c = Cursor(table)
        if c.findFirstRow(criteria):
            return c.getCurrentRow()
        return None


class Table:
    """Jackcess `Table` providing schema inspection and row CRUD backed by Rust."""

    def __init__(
        self,
        db: Database,
        name: str,
        columns: list[Column],
        indexes: list[Index],
        rows: list[Row],
    ) -> None:
        self._db = db
        self._name = name
        self._columns = columns
        self._indexes = indexes
        self._rows = rows
        self._allow_autonum_insert = False
        self._default_cursor: Cursor | None = None

    @classmethod
    def _from_rust_payload(cls, db: Database, payload: dict[str, Any]) -> Table:
        name = str(payload.get("name", ""))
        raw_cols = payload.get("columns", [])
        cols: list[Column] = []
        for idx, c in enumerate(raw_cols):
            cols.append(
                Column(
                    name=str(c.get("name", "")),
                    data_type=str(c.get("type", "TEXT")),
                    length=int(c.get("length", 0)),
                    auto_number=bool(c.get("auto_number", False)),
                    variable_length=bool(c.get("variable", False)),
                    precision=int(c.get("precision", 0)),
                    scale=int(c.get("scale", 0)),
                    col_index=int(c.get("col_index", idx)),
                    col_id=int(c.get("col_id", idx)),
                )
            )
        raw_idxs = payload.get("indexes", [])
        idxs: list[Index] = []
        for ix in raw_idxs:
            idxs.append(
                Index(
                    name=str(ix.get("name", "")),
                    columns=ix.get("columns", []),
                    unique=bool(ix.get("unique", False)),
                    primary_key=bool(ix.get("primary_key", False)),
                )
            )
        raw_rows = payload.get("rows", [])
        raw_rids = payload.get("row_ids", [])
        rows = cls._deserialize_rows(cols, raw_rows, raw_rids)
        return cls(db=db, name=name, columns=cols, indexes=idxs, rows=rows)

    @staticmethod
    def _deserialize_rows(
        cols: list[Column],
        raw_rows: list[dict[str, Any]],
        raw_rids: list[list[int]],
    ) -> list[Row]:
        date_cols = {c.getName() for c in cols if c.getType() == DataType.SHORT_DATE_TIME}
        bin_cols = {c.getName() for c in cols if c.getType() in (DataType.OLE, DataType.BINARY)}
        num_cols = {c.getName() for c in cols if c.getType() in (DataType.NUMERIC, DataType.MONEY)}
        rows: list[Row] = []
        for i, r in enumerate(raw_rows):
            rid_pair = raw_rids[i] if i < len(raw_rids) else [0, i]
            row_dict = dict(r)
            for dc in date_cols:
                v = row_dict.get(dc)
                if isinstance(v, str) and v:
                    try:
                        dt = datetime.datetime.fromisoformat(v)
                        row_dict[dc] = JackcessDateTime(
                            dt.year,
                            dt.month,
                            dt.day,
                            dt.hour,
                            dt.minute,
                            dt.second,
                            dt.microsecond,
                        )
                    except ValueError:
                        pass
            for bc in bin_cols:
                v = row_dict.get(bc)
                if isinstance(v, str):
                    try:
                        row_dict[bc] = base64.b64decode(v)
                    except Exception:
                        pass
            for nc in num_cols:
                v = row_dict.get(nc)
                if isinstance(v, str) and v:
                    try:
                        row_dict[nc] = Decimal(v)
                    except Exception:
                        pass
            rows.append(Row(row_dict, RowId(rid_pair[0], rid_pair[1])))
        return rows

    def _reload(self) -> None:
        res = rust_jackcess_exec(
            {
                "op": "read_table",
                "mdb_path": str(self._db.getFile()),
                "table_name": self._name,
            }
        )
        if res and res.get("ok") and res.get("found"):
            self._rows = self._deserialize_rows(
                self._columns,
                res.get("rows", []),
                res.get("row_ids", []),
            )

    def _serialize_row_map(self, row_map: dict[str, Any]) -> dict[str, Any]:
        col_by_lower = {c.getName().lower(): c for c in self._columns}
        out: dict[str, Any] = {}
        for k, v in row_map.items():
            k_str = k.getName() if hasattr(k, "getName") else str(k)
            col = col_by_lower.get(k_str.lower())
            canon_name = col.getName() if col else k_str
            if v is None:
                out[canon_name] = None
            elif isinstance(v, (bytes, bytearray)):
                if col and col.getType() in (DataType.TEXT, DataType.MEMO):
                    out[canon_name] = bytes(v).decode("utf-8", errors="replace")
                else:
                    out[canon_name] = base64.b64encode(bytes(v)).decode("ascii")
            elif isinstance(v, datetime.datetime):
                out[canon_name] = v.strftime("%Y-%m-%dT%H:%M:%S")
            elif isinstance(v, datetime.date):
                out[canon_name] = f"{v.strftime('%Y-%m-%d')}T00:00:00"
            elif hasattr(v, "getTime") and callable(v.getTime):
                # Java Date object compatibility
                out[canon_name] = int(v.getTime())
            elif isinstance(v, Decimal):
                out[canon_name] = str(v)
            else:
                out[canon_name] = v
        return out

    def getName(self) -> str:
        """Return the table name."""
        return self._name

    def getColumns(self) -> list[Column]:
        """Return all `Column` descriptors in this table."""
        return list(self._columns)

    def getColumn(self, name: str) -> Column:
        """Return a `Column` by name (case-insensitive)."""
        n_low = name.lower()
        for c in self._columns:
            if c.getName().lower() == n_low:
                return c
        raise KeyError(f"Column not found in table {self._name}: {name}")

    def getIndexes(self) -> list[Index]:
        """Return all `Index` descriptors on this table."""
        return list(self._indexes)

    def getIndex(self, name: str) -> Index:
        """Return an `Index` by name (case-insensitive)."""
        n_low = name.lower()
        for ix in self._indexes:
            if ix.getName().lower() == n_low:
                return ix
        raise KeyError(f"Index not found in table {self._name}: {name}")

    def getPrimaryKeyIndex(self) -> Index:
        """Return the PrimaryKey `Index` on this table."""
        for ix in self._indexes:
            if ix.isPrimaryKey() or ix.getName().lower() == "primarykey":
                return ix
        raise KeyError(f"No PrimaryKey index on table {self._name}")

    def getRowCount(self) -> int:
        """Return the current number of active rows in the table."""
        return len(self._rows)

    def getDefaultCursor(self) -> Cursor:
        """Return the table's default `Cursor`."""
        if self._default_cursor is None:
            self._default_cursor = Cursor(self)
        return self._default_cursor

    def newCursor(self) -> CursorBuilder:
        """Return a `CursorBuilder` for this table."""
        return CursorBuilder(self)

    def isAllowAutoNumberInsert(self) -> bool:
        """Return whether explicit values can be inserted into AutoNumber columns."""
        return self._allow_autonum_insert

    def setAllowAutoNumberInsert(self, allow: bool) -> None:
        """Set whether explicit values can be inserted into AutoNumber columns."""
        self._allow_autonum_insert = bool(allow)

    def addRow(self, *values: Any) -> list[Any]:
        """Insert a single row from positional column values (or a single list/tuple)."""
        if len(values) == 1 and isinstance(values[0], (list, tuple)):
            pos_vals = list(values[0])
        else:
            pos_vals = list(values)
        row_map: dict[str, Any] = {}
        for idx, col in enumerate(self._columns):
            if idx < len(pos_vals):
                val = pos_vals[idx]
                if col.isAutoNumber() and (val is None or val == "AUTO_NUMBER"):
                    continue
                row_map[col.getName()] = val
        inserted = self.addRowFromMap(row_map)
        return [inserted.get(c.getName()) for c in self._columns]

    def addRows(self, rows: Iterable[list[Any] | tuple[Any, ...]]) -> list[list[Any]]:
        """Insert multiple rows from positional column value sequences."""
        maps: list[dict[str, Any]] = []
        for pos_vals in rows:
            row_map: dict[str, Any] = {}
            for idx, col in enumerate(self._columns):
                if idx < len(pos_vals):
                    val = pos_vals[idx]
                    if col.isAutoNumber() and (val is None or val == "AUTO_NUMBER"):
                        continue
                    row_map[col.getName()] = val
            maps.append(row_map)
        inserted_maps = self.addRowsFromMaps(maps)
        return [[m.get(c.getName()) for c in self._columns] for m in inserted_maps]

    def addRowFromMap(self, row_map: dict[str, Any]) -> dict[str, Any]:
        """Insert a single row from a column-name dictionary."""
        res = self.addRowsFromMaps([row_map])
        return res[0] if res else dict(row_map)

    def addRowsFromMaps(self, row_maps: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """Insert multiple rows from column-name dictionaries."""
        serialized = [self._serialize_row_map(m) for m in row_maps]
        if not serialized:
            return []
        res = rust_jackcess_exec(
            {
                "op": "add_rows",
                "mdb_path": str(self._db.getFile()),
                "table_name": self._name,
                "rows": serialized,
                "allow_autonum": True,
            }
        )
        if not res or not res.get("ok"):
            err = res.get("error", "Unknown error") if res else "Rust engine unavailable"
            raise RuntimeError(f"Failed to add rows to {self._name}: {err}")
        self._reload()
        n = len(serialized)
        return [dict(r) for r in self._rows[-n:]]

    def updateRow(self, row: Row | dict[str, Any]) -> Row:
        """Update an existing `Row` in the database."""
        if not isinstance(row, Row):
            raise ValueError("updateRow requires a Row obtained from the table or cursor")
        rid = row.getId()
        serialized = self._serialize_row_map(row)
        res = rust_jackcess_exec(
            {
                "op": "update_row",
                "mdb_path": str(self._db.getFile()),
                "table_name": self._name,
                "page_num": rid.getPageNumber(),
                "row_num": rid.getRowNumber(),
                "row": serialized,
            }
        )
        if not res or not res.get("ok"):
            err = res.get("error", "Unknown error") if res else "Rust engine unavailable"
            raise RuntimeError(f"Failed to update row in {self._name}: {err}")
        self._reload()
        for r in self._rows:
            if r.getId() == rid:
                return r
        return row

    def deleteRow(self, row: Row) -> Row:
        """Delete an existing `Row` from the database."""
        rid = row.getId()
        res = rust_jackcess_exec(
            {
                "op": "delete_row",
                "mdb_path": str(self._db.getFile()),
                "table_name": self._name,
                "page_num": rid.getPageNumber(),
                "row_num": rid.getRowNumber(),
            }
        )
        if not res or not res.get("ok"):
            err = res.get("error", "Unknown error") if res else "Rust engine unavailable"
            raise RuntimeError(f"Failed to delete row in {self._name}: {err}")
        self._reload()
        return row

    def reset(self) -> None:
        """Reset the default cursor of this table."""
        if self._default_cursor is not None:
            self._default_cursor.reset()

    def iterator(self) -> Iterator[Row]:
        """Return an iterator over all rows in the table."""
        return iter(list(self._rows))

    def __iter__(self) -> Iterator[Row]:
        return iter(list(self._rows))

    def __len__(self) -> int:
        return len(self._rows)


class TableBuilder:
    """Jackcess `TableBuilder` for creating a new table in a `Database`."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._columns: list[Column] = []
        self._indexes: list[Index] = []

    def addColumn(self, col: ColumnBuilder | Column) -> TableBuilder:
        """Add a single column to the table builder."""
        c = col.toColumn() if isinstance(col, ColumnBuilder) else col
        self._columns.append(c)
        return self

    def addColumns(self, cols: Iterable[ColumnBuilder | Column]) -> TableBuilder:
        """Add multiple columns to the table builder."""
        for col in cols:
            self.addColumn(col)
        return self

    def addIndex(self, idx: IndexBuilder | Index) -> TableBuilder:
        """Add a single index to the table builder."""
        ix = idx.toIndex() if isinstance(idx, IndexBuilder) else idx
        self._indexes.append(ix)
        return self

    def addIndexes(self, idxs: Iterable[IndexBuilder | Index]) -> TableBuilder:
        """Add multiple indexes to the table builder."""
        for idx in idxs:
            self.addIndex(idx)
        return self

    def setPrimaryKey(self, *col_names: str) -> TableBuilder:
        """Add a PrimaryKey index on `col_names`."""
        ib = IndexBuilder(IndexBuilder.PRIMARY_KEY_NAME).addColumns(*col_names).setPrimaryKey()
        self.addIndex(ib)
        return self

    def toTable(self, db: Database) -> Table:
        """Create the table in `db` and return the resulting `Table`."""
        cols_payload = [c.to_dict(i) for i, c in enumerate(self._columns)]
        idxs_payload = [ix.to_dict() for ix in self._indexes]
        res = rust_jackcess_exec(
            {
                "op": "create_table",
                "mdb_path": str(db.getFile()),
                "table_name": self._name,
                "columns": cols_payload,
                "indexes": idxs_payload,
            }
        )
        if not res or not res.get("ok"):
            err = res.get("error", "Unknown error") if res else "Rust engine unavailable"
            raise RuntimeError(f"Failed to create table {self._name}: {err}")
        tbl = db.getTable(self._name)
        if tbl is None:
            raise RuntimeError(f"Table {self._name} not found after creation")
        return tbl


class Database:
    """Jackcess `Database` handle backed by Rust `mm_core_rs`."""

    FileFormat = FileFormat

    def __init__(self, mdb_path: str | Path, file_format: str = FileFormat.V2000) -> None:
        self._path = Path(str(mdb_path))
        self._file_format = file_format
        self._closed = False

    def getFile(self) -> Path:
        """Return the `Path` to the underlying `.mdb` file."""
        return self._path

    def getFileFormat(self) -> str:
        """Return the `FileFormat` identifier string."""
        return self._file_format

    def getTableNames(self) -> set[str]:
        """Return the set of user table names in the database."""
        res = rust_jackcess_exec(
            {
                "op": "get_table_names",
                "mdb_path": str(self._path),
                "include_system": False,
            }
        )
        if not res or not res.get("ok"):
            err = res.get("error", "Unknown error") if res else "Rust engine unavailable"
            raise RuntimeError(f"Failed to read table names from {self._path}: {err}")
        return set(res.get("table_names", []))

    def getSystemTableNames(self) -> set[str]:
        """Return the set of system table names (`MSys*`) in the database."""
        res = rust_jackcess_exec(
            {
                "op": "get_table_names",
                "mdb_path": str(self._path),
                "include_system": True,
            }
        )
        if not res or not res.get("ok"):
            return set()
        user_names = self.getTableNames()
        return set(res.get("table_names", [])) - user_names

    def getTable(self, name: str) -> Table | None:
        """Return the user `Table` with `name`, or `None` if it does not exist."""
        res = rust_jackcess_exec(
            {
                "op": "read_table",
                "mdb_path": str(self._path),
                "table_name": str(name),
            }
        )
        if not res or not res.get("ok"):
            err = res.get("error", "Unknown error") if res else "Rust engine unavailable"
            raise RuntimeError(f"Failed to read table {name} from {self._path}: {err}")
        if not res.get("found"):
            return None
        return Table._from_rust_payload(self, res)

    def getSystemTable(self, name: str) -> Table | None:
        """Return the system `Table` with `name` (e.g. `'MSysObjects'`), or `None`."""
        return self.getTable(name)

    def flush(self) -> None:
        """No-op as Rust operations flush directly to the `.mdb` file."""

    def close(self) -> None:
        """Mark the database handle as closed."""
        self._closed = True

    def __enter__(self) -> Database:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __iter__(self) -> Iterator[Table]:
        for tname in sorted(self.getTableNames()):
            tbl = self.getTable(tname)
            if tbl is not None:
                yield tbl


class DatabaseBuilder:
    """Jackcess `DatabaseBuilder` for opening or creating `.mdb` databases."""

    def __init__(self, file_or_path: str | Path | None = None) -> None:
        self._path: Path | None = Path(str(file_or_path)) if file_or_path is not None else None
        self._file_format: str = FileFormat.V2000
        self._read_only: bool = False
        self._auto_sync: bool = True

    def setFile(self, file_or_path: str | Path) -> DatabaseBuilder:
        """Set the target `.mdb` file path."""
        self._path = Path(str(file_or_path))
        return self

    def setFileFormat(self, file_format: str) -> DatabaseBuilder:
        """Set the `FileFormat` for database creation."""
        self._file_format = str(file_format)
        return self

    def setReadOnly(self, read_only: bool) -> DatabaseBuilder:
        """Configure read-only mode."""
        self._read_only = bool(read_only)
        return self

    def setAutoSync(self, auto_sync: bool) -> DatabaseBuilder:
        """Configure auto-sync mode."""
        self._auto_sync = bool(auto_sync)
        return self

    def open(self: Any = None, file_or_path: str | Path | None = None) -> Database:
        """Open an existing `.mdb` database file (supports both instance and static calls)."""
        if isinstance(self, DatabaseBuilder):
            target = Path(str(file_or_path)) if file_or_path is not None else self._path
            fmt = self._file_format
        else:
            target = Path(str(self)) if self is not None else None
            fmt = FileFormat.V2000
        if target is None:
            raise ValueError("Database file path is required")
        if not target.is_file():
            raise FileNotFoundError(f"MDB file does not exist: {target}")
        return Database(target, fmt)

    def create(
        self: Any = None,
        file_or_path: str | Path | None = None,
    ) -> Database:
        """Create a new empty `.mdb` database file (supports both instance and static calls)."""
        if isinstance(self, DatabaseBuilder):
            target = Path(str(file_or_path)) if file_or_path is not None else self._path
            fmt = self._file_format
        else:
            fmt = str(self) if self is not None else FileFormat.V2000
            target = Path(str(file_or_path)) if file_or_path is not None else None
        if target is None:
            raise ValueError("Database file path is required")
        target.parent.mkdir(parents=True, exist_ok=True)
        res = rust_jackcess_exec(
            {
                "op": "create_db",
                "mdb_path": str(target),
                "file_format": str(fmt),
            }
        )
        if not res or not res.get("ok"):
            err = res.get("error", "Unknown error") if res else "Rust engine unavailable"
            raise RuntimeError(f"Failed to create MDB at {target}: {err}")
        return Database(target, str(fmt))
