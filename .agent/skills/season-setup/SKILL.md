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

### 3. Verification
ALWAYS run the hermetic and integration tests after modifying the setup logic:
```bash
uv run --project backend pytest backend/tests/integration/test_season_setup_hermetic.py
uv run --project backend pytest backend/tests/integration/test_season_setup_full.py
```

## Best Practices
- **Mirror Structure**: The generation script automatically creates a layered folder structure mirroring previous years' Google Drive layouts.
- **Hermetic Tests**: Use `mock_mdb_generator.py` to test transformation logic without requiring real MDB files or a full JRE.
- **Case-Insensitivity**: The `SeasonTransformer` is built to handle inconsistent casing in MDB table and column names (e.g., `Meet` vs `MEET`).
