# Verification Tests

This directory contains the test suite for verifying the correctness of data parsing, restoration, and logical conversion.

## Key Tests

### `test_mdb_verification.py`
The primary verification script for ensuring **data fidelity**. It performs a "round-trip" test on MDB files:
1. reads an MDB source.
2. Dumps it to JSON.
3. Restores it to a new MDB.
4. Dumps the new MDB to JSON.
5. deeply compares the two JSON dumps.

**Usage:**
```bash
uv run tests/test_mdb_verification.py
```
*Note: This script automatically scans for MDB files in `../tmp`.*

### `test_full_cycle.py` (Deprecated/Legacy)
An earlier verification script that tested the logical conversion of `mm_to_json.py` against a specific `Singers23.mdb`. It focuses more on the Python application logic than raw data integrity.

### `test_recreation.py`
A targeted test for verifying the recreation of a specific MDB file (`Singers23.mdb`).

## Test Data

- **Template_Schema.json**: Defines the standard schema structure for creating new MDBs from scratch.
- **Empty_Schema.json**: An empty database definition used for initialization.
- **Sample_Data.mdb**: Generated sample data for testing without using real user files.
