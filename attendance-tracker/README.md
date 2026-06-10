# Attendance Tracker

Automation suite for generating and managing Google Sheets-based swim meet attendance trackers from Meet Manager (.mdb) files.

## Overview

The Attendance Tracker provides a bi-directional, synchronized environment for coaches and volunteers to track swimmer presence and scratches. It automates the extraction of registration data (events and relays) and maintains structural integrity through bound Apps Script logic.

## Directory Structure

- `extract_attendance_data.py`: Python script to extract swimmer info and event registrations from MDB files.
- `populate_sheets.py`: Python script to create/update Google Spreadsheets with data, formatting, and formulas.
- `AttendanceTracker.js`: Source for the bound Google Apps Script (synchronization logic).
- `appsscript.json`: Manifest for the Apps Script project.
- `tests/`: Unit and integration tests.

## Key Features

1. **Granular Event Mapping**: Automatically classifies events into Free, Back, Breast, Fly, IM, Free Relay, and Medley Relay columns.
2. **Bi-directional Sync**: Syncs 'Present' and 'Scratch' status between the 'Main' tab and Age Group tabs.
3. **Dynamic Filtering**: Uses native Google Sheets `FILTER` functions for 'All Scratches' and 'Pending' views.
4. **Professional Formatting**: Automated header styling, frozen rows, and column hiding for metadata.

## Setup & Usage

### Prerequisites
- Python 3.11+
- `gws` CLI (Google Workspace CLI)
- `clasp` (for Apps Script management)
- Access to the `MeetManager-Tools` backend source (for `mm_to_json`).

### Running the Tracker Generation
1. Extract data:
   ```bash
   python extract_attendance_data.py /path/to/meet.mdb
   ```
2. Populate sheet:
   ```bash
   python populate_sheets.py
   ```
3. Push script (if updating logic):
   ```bash
   clasp push
   ```

## Development

Run tests:
```bash
python -m unittest discover tests
```
