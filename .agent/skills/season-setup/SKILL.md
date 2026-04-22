# Season Setup

## Overview
Automates the creation of Meet Manager (MDB) files for a new swim season using a template file. It configures the correct venues, lane counts, age-up dates, and sessions.

## Execution
Run the following targets using `just`:

1.  **Generate a Season:**
    ```bash
    just generate-season <path/to/template.mdb> <path/to/output_dir> [owner_team]
    ```
2.  **Validate against History:**
    ```bash
    just validate-season <path/to/template.mdb> <path/to/historical.mdb>
    ```

## Configuration
Update `backend/scripts/season_setup/config/venues.json` to modify lane counts or add new teams to the league.

Update `SCHEDULE_202X` in `backend/scripts/season_setup/generate_season.py` when preparing for a new year.