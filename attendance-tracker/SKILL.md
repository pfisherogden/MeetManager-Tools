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
- **No Hardcoded Spreadsheet IDs**: Always retrieve the target spreadsheet ID dynamically from environment variables or a local `.env` file (`ATTENDANCE_SPREADSHEET_ID`). Remove `"parentId"` from `clasp.json` to prevent checking it in.
- **Static Column Widths**: Do not auto-resize columns using Google Sheets API or Apps Script. Dynamic tabs like `All Scratches` evaluate formulas asynchronously and will collapse to width 0. Use the predefined user-adjusted pixel widths: `[73, 54, 104, 89, 57, 56, 90, 73, 37, 40, 49, 29, 27, 100, 100, 100, 100]`.
- **Numerical Sorting Hack**: Prepend a space to age groups <= 10 (e.g. `" 6 & Under"`, `" 7-8"`, `" 9-10"`) to force correct numerical ordering in alphabetical sorts. Strip the space when mapping to sheet tab names in python.
- **CodeQL URL Sanitization**: When validating URLs in audit or test scripts, use `urllib.parse` to extract and match `parsed.hostname` exactly. Substring checks (like `in`) trigger CodeQL alerts.

## Verification Checklist
- [ ] 'Main' tab follows Age Group tabs (index 6).
- [ ] Sort order: Age Group -> Gender -> Preferred Name.
- [ ] Relay columns (Medley then Free) appear BEFORE individual strokes.
- [ ] Visual Warnings: Pink for conflicts, Yellow for relay scratches.
- [ ] QR Code tab contains scannable image and valid parsed URL matching the exact target hostname.
- [ ] Bi-directional sync verified (Columns 5/6 using ID Column 14).
- [ ] All temporary files and audit spreadsheets are git-ignored and not checked in.
