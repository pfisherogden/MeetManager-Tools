import json
import logging
import os
from typing import Any

import gspread
import pandas as pd
from google.auth import default

logger = logging.getLogger(__name__)


def _cleanup_old_sheets(gc: gspread.client.Client) -> None:
    """Deletes older attendance tracker spreadsheets from the client's Google Drive.

    Keeps only the 10 most recent spreadsheets matching the pattern
    'Check-in Sheet' or 'Attendance Tracker'.
    """
    import re

    try:
        files = gc.list_spreadsheet_files()
        target_files = []
        for f in files:
            name = f.get("name", "")
            if "Attendance Tracker" in name or "Check-in Sheet" in name:
                target_files.append(f)

        def get_timestamp(f):
            name = f.get("name", "")
            # Look for YYYY-MM-DD HH:MM
            match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", name)
            if match:
                return match.group(0)
            return ""

        target_files.sort(key=get_timestamp)

        # Keep the 10 newest, delete the rest
        if len(target_files) > 10:
            to_delete = target_files[:-10]
            for f in to_delete:
                file_id = f.get("id")
                file_name = f.get("name")
                if isinstance(file_id, str):
                    logger.info(f"Pruning old spreadsheet '{file_name}' ({file_id}) to free up Drive storage quota.")
                    try:
                        gc.del_spreadsheet(file_id)
                    except Exception as del_err:
                        logger.warning(f"Failed to delete spreadsheet {file_id}: {del_err}")
    except Exception as e:
        logger.warning(f"Failed to clean up old spreadsheets: {e}")


class SwimmerCheckInWriter:
    """Generates a Google Spreadsheet or Excel for swimmer check-in with native checkboxes and bi-directional sync."""

    def __init__(self, check_in_data: list[dict[str, Any]], title: str = "Swimmer Check-in"):
        self.data = check_in_data
        self.title = title
        # New Column Order: Last Name, Preferred Name, Present, Scratch, Gender, Age Group, Events..., ID, First Name, Age, Team
        self.visible_cols = [
            "Last Name",
            "Preferred Name",
            "Present",
            "Scratch",
            "Gender",
            "Age Group",
            "Free",
            "Fly",
            "Back",
            "Breast",
            "IM",
            "Free Relay",
            "Medley Relay",
        ]
        self.hidden_cols = ["ID", "First Name", "Age", "Team"]
        self.all_cols = self.visible_cols + self.hidden_cols

    def _prepare_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(self.data)
        # Add status columns if missing
        if "Present" not in df.columns:
            df["Present"] = False
        if "Scratch" not in df.columns:
            df["Scratch"] = False

        # Ensure all required columns exist
        for col in self.all_cols:
            if col not in df.columns:
                df[col] = ""

        # Map 'Present' and 'Scratch' to boolean for native checkbox support
        def to_bool(val):
            v = str(val).upper().strip()
            return v == "TRUE" or v == "X" or v == "CHECKED"

        df["Present"] = df["Present"].apply(to_bool)
        df["Scratch"] = df["Scratch"].apply(to_bool)

        # Reorder
        return df[self.all_cols]

    def generate_google_sheet(self, user_email: str | None = None) -> str:
        """Creates a native Google Sheet with checkboxes, formatting, and Apps Script sync."""
        try:
            # 1. Authenticate
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/script.projects",
            ]
            try:
                credentials, _ = default(scopes=scopes)
            except Exception as e:
                token = os.getenv("GOOGLE_WORKSPACE_CLI_TOKEN")
                if token:
                    from google.oauth2.credentials import Credentials

                    credentials = Credentials(token)
                    logger.info("Using GOOGLE_WORKSPACE_CLI_TOKEN for Google Sheet generation")
                else:
                    raise e

            gc = gspread.authorize(credentials)

            # Clean up old sheets to preserve storage quota (Issue #506)
            _cleanup_old_sheets(gc)

            # 2. Create Spreadsheet
            sheet_title = f"{self.title} - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
            sh = gc.create(sheet_title)

            # 3. Share
            if user_email:
                try:
                    sh.share(user_email, perm_type="user", role="writer")
                except Exception as e:
                    logger.warning(f"Failed to share sheet with {user_email}: {e}")
            try:
                sh.share("", perm_type="anyone", role="reader")
            except Exception:
                pass

            # 4. Populate Main
            df = self._prepare_dataframe()
            main_ws = sh.sheet1
            main_ws.update_title("Main")

            # Update with data
            data_list = [df.columns.tolist()] + df.values.tolist()
            main_ws.update(data_list)

            # Formatting & Checkboxes
            self._apply_native_formatting(main_ws, len(df), is_main=True)
            main_ws.freeze(rows=1)

            # 5. Age Group Tabs (Unified)
            age_groups = ["6 & under", "7-8", "9-10", "11-12", "13-14", "15-18"]
            for group in age_groups:
                subset = df[df["Age Group"] == group]
                if subset.empty:
                    continue
                subset = subset.sort_values(by=["Gender", "Preferred Name"])
                ws = sh.add_worksheet(title=group, rows=len(subset) + 1, cols=len(self.all_cols))

                # Rows with formulas linking to Main for Present/Scratch
                subset_indices = subset.index.tolist()
                header = df.columns.tolist()
                rows = [header]
                for idx in subset_indices:
                    row_data = df.iloc[idx].values.tolist()
                    main_row = idx + 2
                    # Columns C (3) and D (4) are Present/Scratch
                    row_data[2] = f"=Main!C{main_row}"
                    row_data[3] = f"=Main!D{main_row}"
                    rows.append(row_data)

                ws.update(rows, raw=False)
                self._apply_native_formatting(ws, len(subset), is_main=False)
                ws.freeze(rows=1)

            # 6. Dynamic Filter Tabs (Native Sheets Formulas)
            last_row = len(df) + 1
            # Scratches: Column D is Scratch
            scratch_ws = sh.add_worksheet(title="All Scratches", rows=100, cols=len(self.all_cols))
            scratch_ws.update([df.columns.tolist()])
            # Native Sheets FILTER formula: =IFNA(FILTER(Range, Condition), "No Results")
            formula_scratch = f'=IFNA(FILTER(Main!A2:Q{last_row}, Main!D2:D{last_row}=TRUE), "No Scratches")'
            scratch_ws.update([[formula_scratch]], "A2", raw=False)
            self._apply_native_formatting(scratch_ws, 100, is_main=False)

            # Pending: Column C is Present, D is Scratch
            pending_ws = sh.add_worksheet(title="Pending", rows=200, cols=len(self.all_cols))
            pending_ws.update([df.columns.tolist()])
            formula_pending = f'=IFNA(FILTER(Main!A2:Q{last_row}, Main!C2:C{last_row}=FALSE, Main!D2:D{last_row}=FALSE), "All Checked In")'
            pending_ws.update([[formula_pending]], "A2", raw=False)
            self._apply_native_formatting(pending_ws, 200, is_main=False)

            # 7. Install Apps Script
            self._install_apps_script(sh.id)

            return sh.url

        except Exception as e:
            logger.error(f"Failed to generate Google Sheet: {e}", exc_info=True)
            raise

    def _apply_native_formatting(self, ws, num_rows: int, is_main: bool, skip_checkboxes: bool = False):
        """Applies styles, checkboxes, column widths, and hides columns via Batch Update."""
        bg = {"red": 0.2, "green": 0.2, "blue": 0.2} if is_main else {"red": 0.8, "green": 0.8, "blue": 0.8}
        fg = {"red": 1.0, "green": 1.0, "blue": 1.0} if is_main else {"red": 0.0, "green": 0.0, "blue": 0.0}

        requests = [
            # 1. Header Format
            {
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 17,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": bg,
                            "horizontalAlignment": "CENTER",
                            "textFormat": {"bold": True, "foregroundColor": fg},
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)",
                }
            },
            # 2. Column Widths
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                    "properties": {"pixelSize": 150},
                    "fields": "pixelSize",
                }
            },  # Last Name
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
                    "properties": {"pixelSize": 120},
                    "fields": "pixelSize",
                }
            },  # Pref Name
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 4},
                    "properties": {"pixelSize": 70},
                    "fields": "pixelSize",
                }
            },  # Checkboxes
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5},
                    "properties": {"pixelSize": 60},
                    "fields": "pixelSize",
                }
            },  # Gender
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6},
                    "properties": {"pixelSize": 100},
                    "fields": "pixelSize",
                }
            },  # Age Group
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 11},
                    "properties": {"pixelSize": 50},
                    "fields": "pixelSize",
                }
            },  # Individual Events
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 11, "endIndex": 13},
                    "properties": {"pixelSize": 85},
                    "fields": "pixelSize",
                }
            },  # Relays
            # 3. Hide Metadata Columns (13-17: ID, First Name, Age, Team)
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": 13, "endIndex": 17},
                    "properties": {"hiddenByUser": True},
                    "fields": "hiddenByUser",
                }
            },
        ]

        # 4. Add native checkboxes (Columns 2 and 3: Present, Scratch)
        if not skip_checkboxes and num_rows > 0:
            requests.append(
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": 1,
                            "endRowIndex": num_rows + 1,
                            "startColumnIndex": 2,
                            "endColumnIndex": 4,
                        },
                        "rule": {"condition": {"type": "BOOLEAN"}, "showCustomUi": True},
                    }
                }
            )

        ws.spreadsheet.batch_update({"requests": requests})

    def _install_apps_script(self, spreadsheet_id: str):
        """Programmatically installs the cross-tab sync script."""
        try:
            import requests  # type: ignore
            from google.auth.transport.requests import Request

            # Use ambient credentials token or fallback
            token = os.getenv("GOOGLE_WORKSPACE_CLI_TOKEN")
            if not token:
                credentials, _ = default(scopes=["https://www.googleapis.com/auth/script.projects"])
                credentials.refresh(Request())
                token = credentials.token

            headers = {"Authorization": f"Bearer {token}"}

            # 1. Create project
            url_create = "https://script.googleapis.com/v1/projects"
            body_create = {"title": "Swimmer Sync", "parentId": spreadsheet_id}
            res_create = requests.post(url_create, headers=headers, json=body_create)

            if res_create.status_code != 200:
                logger.error(f"Apps Script project creation failed: {res_create.text}")
                return

            script_id = res_create.json().get("scriptId")

            appsscript_json = {
                "timeZone": "America/Los_Angeles",
                "dependencies": {},
                "exceptionLogging": "STACKDRIVER",
                "runtimeVersion": "V8",
                "oauthScopes": ["https://www.googleapis.com/auth/spreadsheets.currentonly"],
            }
            code_gs = """
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Swim Tools')
      .addItem('Check Permissions', 'checkPermissions')
      .addItem('Format Spreadsheet (Run Once)', 'setupSheet')
      .addToUi();
}

function checkPermissions() {
  SpreadsheetApp.getActiveSpreadsheet().toast("Permissions granted successfully! Checkbox sync is active.");
}

function setupSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets();
  const mainSheet = ss.getSheetByName("Main");
  if (!mainSheet) return;

  sheets.forEach(sheet => {
    // 1. Column Widths
    sheet.setColumnWidth(1, 150); // Last Name
    sheet.setColumnWidth(2, 120); // Preferred Name
    sheet.setColumnWidth(3, 70);  // Present
    sheet.setColumnWidth(4, 70);  // Scratch
    sheet.setColumnWidth(5, 60);  // Gender
    sheet.setColumnWidth(6, 100); // Age Group
    for (let c=7; c<=11; c++) sheet.setColumnWidth(c, 50); // Individual Events
    for (let c=12; c<=13; c++) sheet.setColumnWidth(c, 85); // Relays

    // 2. Checkboxes (Column C and D)
    const checkboxRange = sheet.getRange(2, 3, sheet.getLastRow() - 1, 2);
    checkboxRange.insertCheckboxes();

    // Force refresh Boolean values to fix Google Sheets display artifacts
    const values = checkboxRange.getValues();
    for (let r=0; r<values.length; r++) {
      values[r][0] = String(values[r][0]).toUpperCase() === "TRUE";
      values[r][1] = String(values[r][1]).toUpperCase() === "TRUE";
    }
    checkboxRange.setValues(values);

    // 3. Hide Metadata Columns (14-17: ID, First Name, Age, Team)
    sheet.hideColumns(14, 4);

    // Formatting Header
    sheet.getRange("A1:Q1").setFontWeight("bold").setBackground("#d3d3d3").setHorizontalAlignment("center");
  });

  SpreadsheetApp.getUi().alert("Formatting Complete! Native checkboxes, column widths, and hidden columns applied.");
}

function onEdit(e) {
  if (!e || !e.range) return;
  const sheet = e.range.getSheet();
  const name = sheet.getName();
  const row = e.range.getRow();
  const col = e.range.getColumn();

  // Ignore header edits or multi-cell edits
  if (row <= 1 || e.range.getNumRows() > 1 || e.range.getNumColumns() > 1) return;

  // We only sync Present (3) and Scratch (4)
  if (col !== 3 && col !== 4) return;

  const idColIdx = 14; // Hidden ID in Col N
  const swimmerId = sheet.getRange(row, idColIdx).getValue();
  if (!swimmerId) return;

  const newValue = e.value === "TRUE" || e.value === true;
  const colName = col === 3 ? "Present" : "Scratch";

  e.source.getSheets().forEach(targetSheet => {
    if (targetSheet.getName() === name) return;

    const tHeaders = targetSheet.getRange(1, 1, 1, targetSheet.getLastColumn()).getValues()[0];
    const tIdColIdx = tHeaders.indexOf("ID") + 1;
    const tTargetColIdx = tHeaders.indexOf(colName) + 1;
    if (tIdColIdx < 1 || tTargetColIdx < 1) return;

    const ids = targetSheet.getRange(2, tIdColIdx, targetSheet.getLastRow(), 1).getValues();
    for (let i = 0; i < ids.length; i++) {
      if (ids[i][0] == swimmerId) {
        targetSheet.getRange(i + 2, tTargetColIdx).setValue(newValue);
        break;
      }
    }
  });
}
"""
            update_body = {
                "files": [
                    {"name": "appsscript", "type": "JSON", "source": json.dumps(appsscript_json)},
                    {"name": "Code", "type": "SERVER_JS", "source": code_gs},
                ]
            }

            url_update = f"https://script.googleapis.com/v1/projects/{script_id}/content"
            res_update = requests.put(url_update, headers=headers, json=update_body)
            if res_update.status_code != 200:
                logger.error(f"Apps Script content update failed: {res_update.text}")
            else:
                logger.info(f"Installed Apps Script in {spreadsheet_id}")
        except Exception as e:
            logger.error(f"Apps Script installation error: {e}", exc_info=True)

    def generate_excel_backup(self, output_path: str):
        """Generates the Excel file with matching reordered columns and hidden metadata."""
        df = self._prepare_dataframe()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            workbook = writer.book
            header_fmt = workbook.add_format({"bold": True, "bg_color": "#D3D3D3", "border": 1})

            def write_ws(name, data, is_main=False):
                data.to_excel(writer, sheet_name=name, index=False)
                ws = writer.sheets[name]
                for c, val in enumerate(data.columns):
                    ws.write(0, c, val, header_fmt)
                ws.set_column("A:A", 20)
                ws.set_column("B:B", 15)
                ws.set_column("C:D", 10)
                ws.set_column("E:F", 10)
                ws.set_column("G:M", 5)
                ws.set_column("N:Q", None, None, {"hidden": True})
                if not is_main:
                    for i in range(len(data)):
                        row = i + 1
                        m_row = data.index[i] + 2
                        ws.write_formula(row, 2, f"=Main!C{m_row}")
                        ws.write_formula(row, 3, f"=Main!D{m_row}")
                ws.freeze_panes(1, 0)

            write_ws("Main", df, is_main=True)
            for ag in ["6 & under", "7-8", "9-10", "11-12", "13-14", "15-18"]:
                sub = df[df["Age Group"] == ag].sort_values(by=["Gender", "Preferred Name"])
                if not sub.empty:
                    write_ws(ag[:31], sub)

            # 3. Dynamic Tabs
            last_row = len(df) + 1
            # Excel FILTER formula (works in Excel 365 / modern Google Sheets)
            # All Scratches (Col D)
            scr_df = pd.DataFrame(columns=df.columns)
            write_ws("All Scratches", scr_df)
            ws_scr = writer.sheets["All Scratches"]
            ws_scr.write_dynamic_array_formula(
                1, 0, 1, 16, f'=FILTER(Main!A2:Q{last_row}, Main!D2:D=TRUE, "No Scratches")'
            )

            # Pending (Col C and D)
            pen_df = pd.DataFrame(columns=df.columns)
            write_ws("Pending", pen_df)
            ws_pen = writer.sheets["Pending"]
            ws_pen.write_dynamic_array_formula(
                1,
                0,
                1,
                16,
                f'=FILTER(Main!A2:Q{last_row}, (Main!C2:C=FALSE)*(Main!D2:D=FALSE), "All Checked In")',
            )

    def generate_google_sheet_shortcut(self, gs_url: str, output_path: str) -> str:
        """Generates a small HTML file that redirects to the Google Sheet."""
        html = f"<!DOCTYPE html><html><head><meta http-equiv='refresh' content='0; url={gs_url}'></head><body>Redirecting to <a href='{gs_url}'>Google Sheet</a>...</body></html>"
        with open(output_path, "w") as f:
            f.write(html)
        return output_path
