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
  - `columns 3 and 4` are Present/Scratch.

## Critical Constraints
- **Least Privilege**: Always use the `https://www.googleapis.com/auth/spreadsheets.currentonly` scope in `appsscript.json`.
- **Formula Safety**: Never place formulas in Row 1. Use Row 2 (e.g., `A2`) to avoid overwriting headers.
- **Dynamic Protection**: The `onEdit` trigger MUST ignore tabs listed in the `FILTER` formulas (e.g., 'All Scratches', 'Pending') to prevent data corruption.

## Verification Checklist
- [ ] 'Main' tab sorted by Last Name, then Preferred Name.
- [ ] Age Group tabs sorted by Gender, then Preferred Name.
- [ ] Metadata columns (14-17) hidden.
- [ ] Header row frozen and gray.
- [ ] Checkboxes only on rows with swimmer data.
- [ ] Bi-directional sync verified by manual test or sub-agent audit.
