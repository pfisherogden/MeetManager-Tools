# Season Setup Skill

## Overview
Automates the configuration of Meet Manager (MDB) files for a new swim season using a "blank" template. This skill handles data purging, metadata updates (dates, age-up, deadlines), and session consolidation while preserving the host team's configuration.

## Pre-requisites
- **Java Runtime**: Required by Jackcess (run `backend/src/mm_to_json/download_libs.py` if missing).
- **Template MDB**: A base MDB file from a previous season (e.g., "Meet Manager blank template").
- **Isolated Workspace**: ALWAYS use `git worktree` in `.worktrees/` for all generation tasks to prevent clobbering your primary branch.

## Workflow

### 1. Configuration
- **Venues**: Update `backend/scripts/season_setup/config/venues.json` with host pool lane counts.
- **Schedule**: Update `backend/scripts/season_setup/config/schedule.json` with meet dates, names, and hosts.

### 2. Execution
Use the `Justfile` targets from the project root:

- **Generate Season**:
  ```bash
  just generate-season <template_path> <output_dir> [year] [owner_team_abbr]
  ```
- **Validate against History**:
  ```bash
  just validate-season <template_path> <historical_mdb_path>
  ```
- **Sync to Drive**:
  ```bash
  just sync-meets
  ```

## Core Mandates
- **Scoring Rules**:
    - **Dual Meets**: relay scoring is 10-6-0 (Rule 19).
    - **Championships**: individual scoring is 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1 (16 places) and relay scoring is 40-34-32-30-28-26-24-22 (8 places) (Rule 40).
- **Registration Deadline**: Set the entry deadline to **4 days before the meet** (Tuesday for Saturday meets) to accommodate the internal parent registration window.
- **Automated Exports**: Every meet generation MUST produce a "Meet Events-" ZIP file containing `.ev3` and `.hyv` files for Team Manager/TeamUnify import. Use `MeetEventWriter`.

## Verification
ALWAYS run the hermetic and integration tests after modifying the setup logic:
```bash
just test-season-setup
```

## Handling Verification Feedback
If manual verification in the MeetManager Windows application reveals incorrect settings:

1.  **Iterate on Transformation**: Modify the `SeasonTransformer` class in `backend/scripts/season_setup/season_transformer.py`. This is the single source of truth for the JSON-to-JSON transformation.
2.  **Cross-Check Tables**: Use `inspect_template_sessions.py` or similar scripts to identify the exact internal MDB table/column names that MeetManager expects.
3.  **Validate Regressions**: Before finalizing a fix, run `just validate-season` against historical MDBs to ensure the change doesn't break known-good configurations from previous years.

## Best Practices
- **Date Handling**: All date fields in transformed JSON must be converted to **millisecond timestamps** (integers) before restoration.
- **Schema Awareness**: Always pass `table_defs` to `SeasonTransformer` when performing transformations. This ensures that even if a table is empty in the template, its columns are correctly mapped during record creation.
- **Meet Manager Constants**: Standardize dual meet settings:
    - ID Format: 1 (USAS)
    - Host LSC: CC
    - DQ Codes: H (Custom)
- **Mirror Structure**: The generation script automatically creates a layered folder structure mirroring previous years' Google Drive layouts.
