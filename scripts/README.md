# Scripts

Utility scripts for debugging and data management.

## Available Scripts

### `inspect_mdbs.py`
Prints the schema type, logical table counts, and physical table names for a given `.mdb` file.
Usage:
```bash
# From repository root
uv run python scripts/inspect_mdbs.py
```

## Creating New Scripts
- Add scripts here that are not part of the core service logic.
- Ensure they handle imports by adding `backend/src` to `sys.path` if they need the `mm_to_json` package.
