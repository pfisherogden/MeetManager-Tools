import json
import os
import subprocess
from typing import List, Dict, Any, Optional

spreadsheet_id = "1ln0ynFoOHe9jx43Mb2ox6ACP_mhinoAmEtkNJVqdS38"


def run_gws(
    service: str,
    *args: str,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Executes a Google Workspace CLI (gws) command.

    Args:
        service: The GWS service name (e.g., "sheets").
        *args: Sub-resources and method name (e.g., "spreadsheets", "values", "update").
        params: URL/Query parameters as a dictionary.
        body: Request body as a dictionary.

    Returns:
        The parsed JSON response or raw output string.
    """
    cmd = ["gws", service] + list(args)
    if params:
        cmd.extend(["--params", json.dumps(params)])
    if body:
        cmd.extend(["--json", json.dumps(body)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running gws {' '.join(args)}: {result.stderr}")
        return None
    try:
        return json.loads(result.stdout)
    except Exception:
        return result.stdout


def apply_formatting(
    sheet_id: int, row_count: int, is_dynamic: bool = False
) -> List[Dict[str, Any]]:
    """
    Generates a list of batchUpdate requests for formatting a sheet.

    Args:
        sheet_id: The ID of the sheet to format.
        row_count: The number of rows containing data.
        is_dynamic: Whether the sheet is formula-driven (skips checkboxes).

    Returns:
        A list of request dictionaries for spreadsheets.batchUpdate.
    """
    requests = []

    # Column Widths
    # 1:Last Name, 2:Preferred Name, 3:Present, 4:Scratch, 5:Gender, 6:Age Group,
    # 7:Free, 8:Back, 9:Breast, 10:Fly, 11:IM, 12:Free Relay, 13:Medley Relay
    widths = [150, 120, 70, 70, 60, 100, 50, 50, 50, 50, 50, 85, 85]
    for i, w in enumerate(widths):
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": i,
                        "endIndex": i + 1,
                    },
                    "properties": {"pixelSize": w},
                    "fields": "pixelSize",
                }
            }
        )

    # Hide Metadata Columns (13-17) - Indices 13, 14, 15, 16 (ID, First Name, Age, Team)
    requests.append(
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 13,
                    "endIndex": 17,
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        }
    )

    # Header Format (Bold, Centered, Gray Background)
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 17,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "horizontalAlignment": "CENTER",
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                    }
                },
                "fields": "userEnteredFormat(textFormat,horizontalAlignment,backgroundColor)",
            }
        }
    )

    # Frozen Row
    requests.append(
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        }
    )

    # Checkboxes (only if row_count > 0 and not dynamic)
    if row_count > 0 and not is_dynamic:
        requests.append(
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": row_count + 1,
                        "startColumnIndex": 2,
                        "endColumnIndex": 4,
                    },
                    "rule": {"condition": {"type": "BOOLEAN"}, "showCustomUi": True},
                }
            }
        )

    return requests


def populate() -> None:
    """
    Populates the attendance tracker spreadsheet with swimmer data, formulas, and formatting.
    """
    data_file = "attendance_data.json"
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found. Run extraction first.")
        return

    with open(data_file, "r") as f:
        swimmers = json.load(f)

    headers = [
        "Last Name",
        "Preferred Name",
        "Present",
        "Scratch",
        "Gender",
        "Age Group",
        "Free",
        "Back",
        "Breast",
        "Fly",
        "IM",
        "Free Relay",
        "Medley Relay",
        "ID",
        "First Name",
        "Age",
        "Team",
    ]

    sheet_info = {
        "Main": 0,
        "6 & Under": 1016704458,
        "7-8": 164209875,
        "9-10": 1030939583,
        "11-12": 943249488,
        "13-14": 219663982,
        "15-18": 1666842791,
        "All Scratches": 1274802197,
        "Pending": 438457747,
    }

    def format_swimmer(s: Dict[str, Any]) -> List[Any]:
        row = ["" for _ in range(17)]
        row[0] = s.get("Last Name", "")
        row[1] = s.get("Preferred Name", "")
        row[2] = False  # Present
        row[3] = False  # Scratch
        row[4] = s.get("Gender", "")
        row[5] = s.get("Age Group", "")
        row[6] = s.get("Free", "")
        row[7] = s.get("Back", "")
        row[8] = s.get("Breast", "")
        row[9] = s.get("Fly", "")
        row[10] = s.get("IM", "")
        row[11] = s.get("Free Relay", "")
        row[12] = s.get("Medley Relay", "")
        row[13] = s.get("ID", "")
        row[14] = s.get("First Name", "")
        row[15] = s.get("Age", "")
        row[16] = s.get("Team", "")
        return row

    all_requests = []

    # Sort Main: Last Name, Preferred Name
    swimmers.sort(
        key=lambda x: (
            str(x.get("Last Name", "")).lower(),
            str(x.get("Preferred Name", "")).lower(),
        )
    )

    # Populate and Format Main
    main_values = [headers] + [format_swimmer(s) for s in swimmers]
    run_gws(
        "sheets",
        "spreadsheets",
        "values",
        "update",
        params={
            "spreadsheetId": spreadsheet_id,
            "range": "Main!A1",
            "valueInputOption": "RAW",
        },
        body={"values": main_values},
    )
    all_requests.extend(apply_formatting(sheet_info["Main"], len(swimmers)))

    # Group by Age Group
    age_groups: Dict[str, List[Dict[str, Any]]] = {}
    for s in swimmers:
        ag = s.get("Age Group", "Unknown")
        if ag not in age_groups:
            age_groups[ag] = []
        age_groups[ag].append(s)

    for ag, group in age_groups.items():
        if ag in sheet_info:
            # Sort Age Group: Gender, Preferred Name
            group.sort(
                key=lambda x: (
                    str(x.get("Gender", "")),
                    str(x.get("Preferred Name", "")).lower(),
                )
            )
            ag_values = [headers] + [format_swimmer(s) for s in group]
            run_gws(
                "sheets",
                "spreadsheets",
                "values",
                "update",
                params={
                    "spreadsheetId": spreadsheet_id,
                    "range": f"'{ag}'!A1",
                    "valueInputOption": "RAW",
                },
                body={"values": ag_values},
            )
            all_requests.extend(apply_formatting(sheet_info[ag], len(group)))

    # Headers for All Scratches and Pending
    for tab in ["All Scratches", "Pending"]:
        run_gws(
            "sheets",
            "spreadsheets",
            "values",
            "update",
            params={
                "spreadsheetId": spreadsheet_id,
                "range": f"'{tab}'!A1",
                "valueInputOption": "RAW",
            },
            body={"values": [headers]},
        )

    # Formulas for All Scratches and Pending (A2)
    scratches_formula = '=IFERROR(FILTER(Main!A2:Q, Main!D2:D=TRUE), "No Scratches")'
    run_gws(
        "sheets",
        "spreadsheets",
        "values",
        "update",
        params={
            "spreadsheetId": spreadsheet_id,
            "range": "'All Scratches'!A2",
            "valueInputOption": "USER_ENTERED",
        },
        body={"values": [[scratches_formula]]},
    )
    all_requests.extend(
        apply_formatting(sheet_info["All Scratches"], 0, is_dynamic=True)
    )

    pending_formula = '=IFERROR(FILTER(Main!A2:Q, (Main!A2:A<>"") * (Main!C2:C=FALSE) * (Main!D2:D=FALSE)), "No Pending")'
    run_gws(
        "sheets",
        "spreadsheets",
        "values",
        "update",
        params={
            "spreadsheetId": spreadsheet_id,
            "range": "Pending!A2",
            "valueInputOption": "USER_ENTERED",
        },
        body={"values": [[pending_formula]]},
    )
    all_requests.extend(apply_formatting(sheet_info["Pending"], 0, is_dynamic=True))

    # Run all formatting requests
    run_gws(
        "sheets",
        "spreadsheets",
        "batchUpdate",
        params={"spreadsheetId": spreadsheet_id},
        body={"requests": all_requests},
    )

    print("Data population and formatting complete.")


if __name__ == "__main__":
    populate()
