# Season Setup Automation

This directory contains tools to automate the configuration of MeetManager `.mdb` files for a new swim season. It uses a base "blank" template from a previous season and transforms it into a set of `.mdb` files customized for the new schedule.

## Features

- **Automated Configuration**: Sets meet dates, age-up dates, and entry deadlines. Note: Dates are stored internally as millisecond timestamps to ensure compatibility with MDB restoration.
- **Venue-Aware**: Uses `config/venues.json` to automatically configure lanes and facility addresses.
- **Scoring Logic**: Automatically applies the league standard 5-3-2-1 / 10-6 scoring rules for dual meets.
- **Session Consolidation**: Automatically consolidates all events into "Session 1" for standard dual meets.
- **Team Management**: Purges old data but preserves host team identity. Robustly adds missing teams using schema-aware mapping.
...
### Execution Environment

It is highly recommended to run these tools inside the `backend` Docker container to ensure all Java dependencies (JPype, Jackcess) are correctly configured.

```bash
docker compose run --rm backend just generate-season <args>
```
- **Configurable**: Easily adaptable for teams other than Del Prado via the `--owner-team` argument.

## Requirements

- Python 3.11+
- `uv` package manager (configured in project root)
- A Java Runtime (required by JPype/Jackcess to read/write `.mdb` files)

## Usage

### 1. Generating a Season

You need a blank or base `.mdb` template file. To generate the season:

```bash
just generate-season <path/to/template.mdb> <path/to/output_dir> [owner_team]
```
*(If `owner_team` is omitted, it defaults to `DP`)*

Example:
```bash
just generate-season ../../templates/blank.mdb ../../2026_meets DP
```

### 2. Validating Against History

To ensure the transformation logic matches historical configurations, you can validate the template transformation against previous years' actual `.mdb` files.

```bash
just validate-season <path/to/template.mdb> <path/to/historical.mdb> [<path/to/other.mdb> ...]
```

Example:
```bash
just validate-season ../../templates/blank.mdb ../../2024_meets/FAST.mdb ../../2025_meets/BC.mdb
```

## Configuration

### `config/venues.json`

This file holds the mapping of pool locations to their number of lanes, as well as standard team abbreviations and names. Update this file if a pool changes its configuration or a new team joins the league.

```json
{
  "venues": {
    "FAST": 8,
    "Del Prado Cabana Club": 6
  },
  "teams": {
    "DP": "Del Prado Stingrays",
    "CW": "Castlewood Barracudas"
  }
}
```

## Iterating on MDB Configuration

If verification in the MeetManager Windows application reveals incorrect settings (e.g., scoring rules not applying correctly, or session metadata missing):

1.  **Modify `season_transformer.py`**: This class contains the logic for transforming the template JSON. Add or adjust methods here (like `setup_scoring_and_seeding` or `update_meet`) to target the specific tables and columns identified in MeetManager.
2.  **Use `validate_historical.py`**: Before regenerating the current season, run the validation script against previous years' known-good MDB files to ensure your changes accurately reflect the desired state and don't introduce regressions.
3.  **Run Hermetic Tests**: Execute `uv run --project backend pytest tests/integration/test_season_setup_hermetic.py` to verify the transformation logic using randomized mock data.
4.  **Regenerate Season**: Once the logic is verified, run the `generate-season` target to produce fresh 2026 MDB files.

## Updating the Schedule

To configure a new season, update the `SCHEDULE_2026` array (or rename it appropriately for the current year) inside `generate_season.py`.