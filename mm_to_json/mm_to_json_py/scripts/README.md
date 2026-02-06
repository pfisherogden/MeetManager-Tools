# Utility Scripts

This directory contains utility scripts for low-level interaction with MDB files.

## Core Tools

### `dump_mdb.py`
Exports the contents of an MDB file to a raw JSON format. This preserves the exact table and column structure, including data types.

**Usage:**
```bash
uv run scripts/dump_mdb.py <input.mdb> <output.json>
```

### `restore_mdb.py`
Reconstructs an MDB file from a JSON dump creating by `dump_mdb.py`. This is useful for "round-trip" verification or programmatically modifying data in JSON and writing it back.

**Usage:**
```bash
uv run scripts/restore_mdb.py <input.json> <output.mdb>
```

### `generate_sample_data.py`
Generates a new, synthetic MDB file populated with random swim meet data (teams, athletes, events, entries). It uses an empty schema template as a base.

**Usage:**
```bash
uv run scripts/generate_sample_data.py <template_schema.json> <output.mdb>
```

## Inspection Tools

### `check_autonumber.py`
Inspects an MDB file to identify which columns are `AutoNumber` (Counter) types. This helps in understanding how primary keys are managed.

**Usage:**
```bash
uv run scripts/check_autonumber.py <input.mdb>
```

### `doc_schema.py`
Analyzes an MDB file and prints the schema (table names and column types) to stdout.

**Usage:**
```bash
uv run scripts/doc_schema.py <input.mdb>
```
