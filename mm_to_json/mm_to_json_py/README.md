# MeetManager Tools (Python)

A Python implementation of tools for interacting with Hy-Tek Meet Manager `.mdb` databases. This project provides capabilities to read, write, and modify Meet Manager database files using **Jackcess** (a Java library) bridged to Python via `jpype`.

## Features

- **MDB Parsing**: Extract data from MDB files into JSON format.
- **MDB Restoration**: Reconstruct valid MDB files from JSON dumps.
- **Schema Validation**: Verify schema integrity across different Meet Manager versions (2023, 2024, 2025).
- **Data Editing**: programmatic API for creating sessions, teams, athletes, and entries.

## Prerequisites

- **Python 3.10+**
- **Java 17+ (JDK)**: Required for the `jackcess` library interactions.
  - The system will look for `JAVA_HOME` or attempt to use the bundled JDK path in `src/mm_to_json/mdb_writer.py` (though `JAVA_HOME` is preferred).
- **uv**: Recommended package manager.

## Installation

1. Install `uv` (if not installed):
   ```bash
   pip install uv
   ```

2. Sync dependencies:
   ```bash
   uv sync
   ```

## Usage

### Converting MDB to JSON

```bash
uv run src/mm_to_json/mm_to_json.py <input.mdb> > output.json
```

### Development Scripts

See `scripts/README.md` for details on utility scripts for dumping, restoring, and inspecting MDB files.

## Testing

Run the comprehensive verification suite to ensure data integrity across historical files:

```bash
uv run tests/test_mdb_verification.py
```

This will:
1. Scan for MDB files in `../tmp/SwimMeets*`.
2. Convert them to JSON and back to MDB.
3. Compare the original and restored versions to ensure 100% data fidelity.
4. Generate a report in `verification_report.md`.
