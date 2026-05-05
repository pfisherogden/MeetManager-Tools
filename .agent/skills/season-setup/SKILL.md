# Season Setup Skill

## Overview
Automates the configuration of Meet Manager (MDB) files for a new swim season using a "blank" template. This skill handles data purging, metadata updates (dates, age-up, deadlines), and session consolidation while preserving the host team's configuration.

## Pre-requisites
- **Java Runtime**: Required by Jackcess (run `backend/src/mm_to_json/download_libs.py` if missing).
- **Template MDB**: A base MDB file from a previous season (e.g., "Meet Manager blank template").

## Workflow

### 1. Configuration
- **Venues**: Update `backend/scripts/season_setup/config/venues.json` with host pool lane counts.
- **Schedule**: Update the `SCHEDULE_202X` list in `backend/scripts/season_setup/generate_season.py` with meet dates, names, and hosts.

### 2. Execution
Use the `Justfile` targets from the project root:

- **Generate Season**:
  ```bash
  just generate-season <template_path> <output_dir> [owner_team_abbr]
  ```
- **Validate against History**:
  ```bash
  just validate-season <template_path> <historical_mdb_path>
  ```

## Verification
ALWAYS run the hermetic and integration tests after modifying the setup logic:
```bash
uv run --project backend pytest backend/tests/integration/test_season_setup_hermetic.py
uv run --project backend pytest backend/tests/integration/test_season_setup_full.py
```

## Handling Verification Feedback
If manual verification in the MeetManager Windows application reveals incorrect settings (e.g., scoring rules not applying correctly, or session metadata missing):

1.  **Iterate on Transformation**: Modify the `SeasonTransformer` class in `backend/scripts/season_setup/season_transformer.py`. This is the single source of truth for the JSON-to-JSON transformation.
2.  **Cross-Check Tables**: Use `inspect_template_sessions.py` or similar scripts to identify the exact internal MDB table/column names that MeetManager expects.
3.  **Validate Regressions**: Before finalizing a fix, run `just validate-season` against historical MDBs to ensure the change doesn't break known-good configurations from previous years.

## Best Practices
- **Date Handling**: All date fields in transformed JSON must be converted to **millisecond timestamps** (integers) before restoration.
- **Schema Awareness**: Always pass `table_defs` to `SeasonTransformer` when performing transformations. This ensures that even if a table is empty in the template, its columns are correctly mapped during record creation.
- **Docker First**: Run MDB generation and validation inside the `backend` Docker container. This avoids local JRE/library conflicts and ensures consistent results.
- **Meet Manager Constants**: Standardize dual meet settings:
    - ID Format: 1 (USAS)
    - Host LSC: CC
    - DQ Codes: H (Custom)
    - Scoring: 5, 3, 2, 1 (Individual), 10, 6 (Relay)
- **Mirror Structure**: The generation script automatically creates a layered folder structure mirroring previous years' Google Drive layouts.
