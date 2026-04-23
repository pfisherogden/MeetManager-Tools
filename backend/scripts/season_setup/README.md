# Season Setup Automation

This directory contains tools to automate the configuration of MeetManager `.mdb` files for a new swim season. It uses a base "blank" template from a previous season and transforms it into a set of `.mdb` files customized for the new schedule.

## Features

- **Automated Configuration**: Sets meet dates, age-up dates, and entry deadlines based on a provided schedule.
- **Venue-Aware**: Uses `config/venues.json` to automatically configure the correct number of lanes based on the host pool (e.g., FAST=8 lanes, DP=6 lanes).
- **Session Consolidation**: Automatically consolidates all events into "Session 1" for standard dual meets, while preserving multi-session layouts for Championship meets.
- **Team Management**: Purges old opponent data but preserves the host team's identity. Automatically adds missing teams (like new or returning league members).
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

## Updating the Schedule

To configure a new season, update the `SCHEDULE_2026` array (or rename it appropriately for the current year) inside `generate_season.py`.