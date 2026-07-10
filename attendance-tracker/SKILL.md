# Attendance Tracker Skill

Expert guidance for maintaining and extending the MeetManager Attendance Tracker automation.

## Core Workflows

### 1. Generating a New Tracker
1. **Extract**: Run `extract_attendance_data.py` with the path to the season's `.mdb` file.
   - Verify `attendance_data.json` contains the expected number of swimmers and event markers ('X').
2. **Populate**: Update `spreadsheet_id` and `sheet_info` (sheet IDs) in `populate_sheets.py`.
   - Run `populate_sheets.py`.
   - Verify the 'Main' tab and Age Group tabs are populated and styled.
3. **Sync**: If it's a new spreadsheet, use `clasp create --parentId <ID>` and `clasp push` to bind `AttendanceTracker.js`.

### 2. Modifying Event Classification
- The classification logic resides in `extract_attendance_data.py`.
- To add a new event type (e.g., "Open Water"):
  1. Add a new column to the `headers` in `populate_sheets.py`.
  2. Add the corresponding key to the athlete dictionary in `extract_attendance_data.py`.
  3. Update the keyword matching loop to set the 'X' marker.

### 3. Adjusting Sync Logic
- The bi-directional sync is handled by `AttendanceTracker.js`.
- **Constraint**: If the spreadsheet column order changes, you MUST update the column indices in the script:
  - `column 14` is currently the unique ID.
  - `columns 5 and 6` are Present/Scratch.

## Detailed New Meet Workflow

When a new `.mdb` file arrives for a meet:

1.  **Create Spreadsheet**:
    ```bash
    gws sheets spreadsheets create --json '{"properties": {"title": "2026 Attendance Tracker - Meet [N]"}}'
    ```
    - Copy the `spreadsheetId` from the output.
2.  **Add Tabs**:
    - Use `gws sheets spreadsheets batchUpdate` to add the required tabs (indices 0-9): '6 & Under', '7-8', '9-10', '11-12', '13-14', '15-18', 'Main', 'All Scratches', 'Not Checked In', and 'QR Code'.
    - Record the `sheetId` for each new tab.
3.  **Update Config**:
    - In `populate_sheets.py`, update `spreadsheet_id` and the `sheet_info` dictionary with the new IDs.
4.  **Execute & Bind**:
    - Run `just run /path/to/new_meet.mdb`.
    - Run `clasp create --parentId <NEW_ID>` then `just push-script`.

## Critical Constraints
- **Least Privilege**: Always use the `https://www.googleapis.com/auth/spreadsheets.currentonly` scope in `appsscript.json`.
- **Formula Safety**: Never place formulas in Row 1. Use Row 2 (e.g., `A2`) to avoid overwriting headers.
- **Dynamic Protection**: The `onEdit` trigger MUST ignore tabs listed in the `FILTER` formulas (e.g., 'All Scratches', 'Not Checked In') to prevent data corruption.
- **No Hardcoded Resource IDs**: Always load Google Spreadsheet IDs, credentials, or target folder IDs dynamically from environment variables or a local `.env` file rather than hardcoding them. Ensure bound script configurations (like `.clasp.json` `"parentId"`) do not contain hardcoded IDs in tracked files.
- **Static Column Sizing**: Avoid auto-resizing columns via APIs or scripts directly after population if the sheet contains asynchronous formulas (e.g. `FILTER` referencing empty sheets), as they will collapse to 0. Use pre-calculated static column widths based on user-optimized layouts, or delay resizing until formulas evaluate.
- **Sort Ordering Hack**: For alphanumeric columns that require custom ordering (like Age Groups), use character-padding (like leading spaces) to force default alphabetical sorting into correct numerical order, stripping the padding where necessary in code.
- **Secure URL Validation**: When validating URLs or endpoints in tests, audits, or automation scripts, parse them using standard URL parsing libraries (e.g., Python's `urllib.parse`) and validate components (like `hostname`) exactly. Avoid loose substring containment checks (like `in`), which trigger CodeQL security alerts.

## Verification Checklist
- [ ] 'Main' tab follows Age Group tabs (index 6).
- [ ] Sort order: Age Group -> Gender -> Preferred Name.
- [ ] Relay columns (Medley then Free) appear BEFORE individual strokes.
- [ ] Visual Warnings: Pink for conflicts, Yellow for relay scratches.
- [ ] QR Code tab contains scannable image and valid parsed URL matching the exact target hostname.
- [ ] Bi-directional sync verified (Columns 5/6 using ID Column 14).
- [ ] All temporary files and audit spreadsheets are git-ignored and not checked in.

## Operational & Running Constraints

### 1. Spaced File Paths in Justfile Recipes
- **Problem**: Justfile recipes like `just extract mdb_path` do not support path arguments containing spaces out of the box because the command arguments are evaluated in shell context without automatic outer quoting.
- **Workaround**: Copy the target `.mdb` file to a temporary location without spaces (e.g. `attendance-tracker/.tmp/meet.mdb`) prior to running the recipe:
  ```bash
  mkdir -p attendance-tracker/.tmp
  cp "/path/with spaces/meet.mdb" attendance-tracker/.tmp/meet.mdb
  just extract .tmp/meet.mdb
  ```

### 2. Host Disk Space Cleanups
- **Problem**: Unzipping championship-scale `.zip` backups and downloading spreadsheets for local auditing can quickly exhaust host storage.
- **Rule**: Always clean up unzipped folders and downloaded sheets immediately after completion. Note that extracted Windows `.mdb` files may have read-only bits that block simple `rm -rf`. Force clean them using:
  ```bash
  chmod -R 777 attendance-tracker/.tmp && rm -rf attendance-tracker/.tmp
  rm -f attendance-tracker/audit_sheet.xlsx
  ```

### 3. Local Host Test Execution (macOS)
- **Problem**: Running the full backend test suite (`just test-backend-local`) on a macOS host fails due to `weasyprint` expecting `libgobject-2.0-0` (which is usually not present outside the Docker containers).
- **Rule**: To run backend tests on the host without Docker container dependencies, ignore the WeasyPrint test suite:
  ```bash
  cd backend && PYTHONPATH=src:scripts/season_setup uv run pytest tests/ --ignore=tests/test_weasy_reporting.py
  ```

