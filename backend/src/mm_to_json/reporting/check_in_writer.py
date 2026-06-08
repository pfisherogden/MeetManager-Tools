import logging
import os
from typing import Any

import gspread
import pandas as pd
from google.auth import default

logger = logging.getLogger(__name__)


class SwimmerCheckInWriter:
    """Generates a Google Spreadsheet or Excel for swimmer check-in."""

    def __init__(self, check_in_data: list[dict[str, Any]], title: str = "Swimmer Check-in"):
        self.data = check_in_data
        self.title = title

    def generate_google_sheet(self, user_email: str | None = None) -> str:
        """
        Creates a Google Sheet and returns the URL.
        Optionally shares it with the user_email.
        """
        try:
            # 1. Authenticate
            credentials, _ = default(
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
            )
            gc = gspread.authorize(credentials)

            # 2. Create Spreadsheet
            sheet_title = f"{self.title} - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
            sh = gc.create(sheet_title)

            # 3. Share with user if provided
            if user_email:
                try:
                    sh.share(user_email, perm_type="user", role="writer")
                    logger.info(f"Shared check-in sheet with {user_email}")
                except Exception as e:
                    logger.warning(f"Failed to share sheet with {user_email}: {e}")

            # 4. Prepare Data
            df = pd.DataFrame(self.data)
            df.insert(0, "ID", range(1, len(df) + 1))
            df["Present"] = ""
            df["Scratch"] = ""

            # 5. Populate Main Sheet
            main_ws = sh.sheet1
            main_ws.update_title("Main")

            data_list = [df.columns.values.tolist()] + df.values.tolist()
            main_ws.update(data_list)

            # Formatting Main
            main_ws.format(
                "A1:J1",
                {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                    "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                },
            )
            main_ws.freeze(rows=1)

            # 6. Add Filtered Tabs
            groups = [
                ("Girls", "F", "6 & under"),
                ("Boys", "M", "6 & under"),
                ("Girls", "F", "7-8"),
                ("Boys", "M", "7-8"),
                ("Girls", "F", "9-10"),
                ("Boys", "M", "9-10"),
                ("Girls", "F", "11-12"),
                ("Boys", "M", "11-12"),
                ("Girls", "F", "13-14"),
                ("Boys", "M", "13-14"),
                ("Girls", "F", "15-18"),
                ("Boys", "M", "15-18"),
            ]

            for label, gender_code, age_group in groups:
                if df.empty:
                    continue
                subset = df[(df["Gender"] == gender_code) & (df["Age Group"] == age_group)]
                if subset.empty:
                    continue

                ws_name = f"{label} {age_group}"[:31]
                ws = sh.add_worksheet(title=ws_name, rows=len(subset) + 1, cols=10)

                subset_indices = subset.index.tolist()
                header = df.columns.values.tolist()
                rows = [header]
                for idx in subset_indices:
                    row_data = df.iloc[idx].values.tolist()
                    main_row = idx + 2
                    row_data[8] = f"=Main!I{main_row}"
                    row_data[9] = f"=Main!J{main_row}"
                    rows.append(row_data)

                ws.update(rows, raw=False)
                ws.format(
                    "A1:J1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8}}
                )
                ws.freeze(rows=1)

            # 7. Add Scratches Tab
            scratches_ws = sh.add_worksheet(title="All Scratches", rows=100, cols=10)
            scratches_ws.update([df.columns.values.tolist()])
            last_row = len(df) + 1
            filter_formula = f'=FILTER(Main!A2:J{last_row}, Main!J2:J{last_row}="X")'
            # Use update with raw=False for formulas
            scratches_ws.update(values=[[filter_formula]], range_name="A2", raw=False)
            scratches_ws.format(
                "A1:J1", {"textFormat": {"bold": True}, "backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.8}}
            )

            return sh.url

        except Exception as e:
            logger.error(f"Failed to generate Google Sheet: {e}", exc_info=True)
            raise

    def generate_google_sheet_shortcut(self, gs_url: str, output_path: str) -> str:
        """Generates a small HTML file that redirects to the Google Sheet."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Redirecting to Google Sheet...</title>
            <meta http-equiv="refresh" content="0; url={gs_url}">
            <style>
                body {{ font-family: sans-serif; text-align: center; padding: 50px; color: #333; }}
                .loader {{ border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 30px; height: 30px; animation: spin 2s linear infinite; margin: 20px auto; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                a {{ color: #3498db; text-decoration: none; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h2>Opening Swimmer Check-in Sheet...</h2>
            <div class="loader"></div>
            <p>If you are not redirected automatically, <a href="{gs_url}">click here to open the sheet</a>.</p>
            <p style="font-size: 0.8em; color: #666; margin-top: 30px;">(This is a live native Google Sheet shared with your account)</p>
        </body>
        </html>
        """
        with open(output_path, "w") as f:
            f.write(html)
        return output_path

    def generate_excel_backup(self, output_path: str):
        """Generates the Excel file with print-friendly formatting."""
        df = pd.DataFrame(self.data)
        df.insert(0, "ID", range(1, len(df) + 1))
        df["Present"] = ""
        df["Scratch"] = ""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            workbook = writer.book

            # Formats
            header_fmt = workbook.add_format({"bold": True, "bg_color": "#D3D3D3", "border": 1})

            # 1. Main Sheet
            df.to_excel(writer, sheet_name="Main", index=False)
            main_sheet = writer.sheets["Main"]

            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                main_sheet.write(0, col_num, value, header_fmt)

            # Set column widths
            main_sheet.set_column("A:A", 5)  # ID
            main_sheet.set_column("B:D", 15)  # Names
            main_sheet.set_column("E:F", 8)  # Gender/Age
            main_sheet.set_column("G:G", 25)  # Team
            main_sheet.set_column("H:H", 15)  # Age Group
            main_sheet.set_column("I:J", 10)  # Present/Scratch

            main_sheet.freeze_panes(1, 0)

            # 2. Filtered Tabs
            groups = [
                ("Girls", "F", "6 & under"),
                ("Boys", "M", "6 & under"),
                ("Girls", "F", "7-8"),
                ("Boys", "M", "7-8"),
                ("Girls", "F", "9-10"),
                ("Boys", "M", "9-10"),
                ("Girls", "F", "11-12"),
                ("Boys", "M", "11-12"),
                ("Girls", "F", "13-14"),
                ("Boys", "M", "13-14"),
                ("Girls", "F", "15-18"),
                ("Boys", "M", "15-18"),
            ]

            for label, gender_code, age_group in groups:
                if df.empty:
                    continue
                subset = df[(df["Gender"] == gender_code) & (df["Age Group"] == age_group)]
                if subset.empty:
                    continue

                sheet_name = f"{label} {age_group}"[:31]
                subset_indices = subset.index
                subset.to_excel(writer, sheet_name=sheet_name, index=False)
                ws = writer.sheets[sheet_name]

                # Headers
                for col_num, value in enumerate(df.columns.values):
                    ws.write(0, col_num, value, header_fmt)

                # Column Widths
                ws.set_column("A:A", 5)
                ws.set_column("B:D", 15)
                ws.set_column("E:F", 8)
                ws.set_column("G:G", 25)
                ws.set_column("H:H", 15)
                ws.set_column("I:J", 10)

                # Formulas for sync
                for i, original_idx in enumerate(subset_indices):
                    excel_row = i + 1  # xlsxwriter is 0-indexed for rows, but 0 is header
                    main_excel_row = original_idx + 2  # Excel is 1-indexed
                    ws.write_formula(excel_row, 8, f"=Main!I{main_excel_row}")
                    ws.write_formula(excel_row, 9, f"=Main!J{main_excel_row}")

            # 3. All Scratches
            scratches_df = pd.DataFrame(columns=df.columns)
            scratches_df.to_excel(writer, sheet_name="All Scratches", index=False)
            ws_scratches = writer.sheets["All Scratches"]
            for col_num, value in enumerate(df.columns.values):
                ws_scratches.write(0, col_num, value, header_fmt)

            # Formula (Note: FILTER is an array formula)
            last_row = len(df) + 1
            ws_scratches.write_dynamic_array_formula(
                1, 0, last_row, 9, f'=FILTER(Main!A2:J{last_row}, Main!J2:J{last_row}="X", "No Scratches")'
            )

        return output_path
