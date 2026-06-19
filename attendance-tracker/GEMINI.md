# Attendance Tracker: Project Knowledge

## **CRITICAL: Architectural Mandates**

### 1. Source of Truth (Synchronization)
- **ID-Based Lookup**: The `AttendanceTracker.js` script MUST use the unique athlete ID (Column 14) for all synchronization. NEVER rely on row indices or names as they change with sorting.
- **Bi-directional Flow**: Changes in 'Main' must propagate to Age Group tabs, and vice versa.
- **Formula Protection**: `onEdit` MUST explicitly ignore 'All Scratches' and 'Pending' tabs to prevent circular updates or formula overwrite.

### 2. Spreadsheet Structure
- **Frozen Header Row**: Row 1 must ALWAYS be frozen across all tabs.
- **Header Styling**: Gray background (#E6E6E6), Bold, Centered.
- **Hidden Metadata**: Columns 14-17 (ID, First Name, Age, Team) MUST be hidden by default to keep the UI clean.
- **Dynamic Formulas**: Formulas in 'All Scratches' and 'Not Checked In' MUST reside in cell **A2** to preserve the header row (A1).
- **Static Column Widths**: Avoid dynamic auto-resizing on empty dynamic tabs containing formulas (e.g. `FILTER`), as they will collapse. Use predefined static pixel widths representing user-optimized layouts.
- **Numerical Sorting Hack**: Use character-padding (like leading spaces) on alphanumeric columns that combine alphabetical and numerical sort characteristics to guarantee correct numerical sorting order. Strip this padding in code where necessary.

### 3. Data Extraction
- **Relay Athlete Iteration**: Relays MUST be extracted by iterating over the `relayAthletes` field in the MDB JSON to ensure individual swimmers are marked.
- **Keyword Matching**: Use broad but precise keywords for stroke classification (e.g., "freestyle relay" for Free Relay, "im" or "medley" for IM).

## **Standardized Workflow (Project-Wide Alignment)**

### Phase 1: Research & Discovery
- Validate assumptions against the source MDB before population.
- Use `just audit` to trigger sub-agent structural checks after changes.

### Phase 2: Design & Strategy
- Propose changes to the `attendance-tracker` skill or GEMINI.md before implementation.
- Document any column shift that impacts the Apps Script index (Column 14).

### Phase 3: Surgical Implementation
- **Documentation**: All new Python functions MUST include type hints and Google-style docstrings.
- **Dependency Protocol**: Use `uv` or `pip` to maintain local environments. Ensure `gws` and `clasp` are configured.

### Phase 4: Verification & Closure
- **Mandatory Quality Check**: ALWAYS run `just fix` and `just test` before submitting changes.
- **Sanitization**: NEVER check in spreadsheet IDs or URLs to public GitHub issues or documentation. Use the `[Sanitized_Title]` pattern if needed.
- **CodeQL URL Parsing**: Always use `urllib.parse` and check `parsed.hostname` exactly when validating URLs or hosts in tests/audits. Substring checks like `in` trigger security scanning alerts.

## Common Maintenance Tasks

### Updating the Bound Script
1. Edit `AttendanceTracker.js`.
2. Run `just push-script`.

### Modifying Column Layouts
1. Update `apply_formatting` in `populate_sheets.py`.
2. **IMPORTANT**: Update lookup index in `AttendanceTracker.js` if Column 14 moves.

### Troubleshooting Sync Issues
- Check Apps Script execution logs.
- Verify ID column uniqueness.
- Ensure `https://www.googleapis.com/auth/spreadsheets.currentonly` scope is present.
