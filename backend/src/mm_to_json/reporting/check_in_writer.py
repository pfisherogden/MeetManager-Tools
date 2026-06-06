import os
from typing import Any

import pandas as pd


class SwimmerCheckInWriter:
    """Generates an Excel spreadsheet for swimmer check-in with synced tabs."""

    def __init__(self, check_in_data: list[dict[str, Any]], title: str = "Swimmer Check-in"):
        self.data = check_in_data
        self.title = title

    def generate(self, output_path: str):
        """Generates the multi-tab Excel file."""
        df = pd.DataFrame(self.data)

        # Add columns for tracking
        df["Present"] = ""
        df["Scratch"] = ""

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # 1. Main Master Sheet
            # Add an index column for stable referencing
            df.insert(0, "ID", range(1, len(df) + 1))
            df.to_excel(writer, sheet_name="Main", index=False)

            main_sheet = writer.sheets["Main"]

            # Data validation for Present/Scratch
            from openpyxl.worksheet.datavalidation import DataValidation

            dv = DataValidation(type="list", formula1='"X,"', allow_blank=True)
            main_sheet.add_data_validation(dv)

            # Columns I and J are Present and Scratch (0-indexed: 8 and 9)
            last_row = len(df) + 1
            dv.add(f"I2:J{last_row}")

            # 2. Filtered Tabs by Age/Gender
            # Mapping from display name to internal codes
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
                subset = df[(df["Gender"] == gender_code) & (df["Age Group"] == age_group)]
                if subset.empty:
                    continue

                sheet_name = f"{label} {age_group}"[:31]
                subset_indices = subset.index

                subset.to_excel(writer, sheet_name=sheet_name, index=False)
                ws = writer.sheets[sheet_name]

                # Replace Present/Scratch columns with formulas pointing back to Main
                for i, original_idx in enumerate(subset_indices):
                    excel_row = i + 2  # 1-based, plus header
                    main_excel_row = original_idx + 2
                    ws.cell(row=excel_row, column=9).value = f"=Main!I{main_excel_row}"
                    ws.cell(row=excel_row, column=10).value = f"=Main!J{main_excel_row}"

            # 3. Dynamic "All Scratches" Tab
            scratches_df = pd.DataFrame(columns=df.columns)
            scratches_df.to_excel(writer, sheet_name="All Scratches", index=False)
            ws_scratches = writer.sheets["All Scratches"]
            # Modern FILTER formula
            ws_scratches["A2"] = f'=_xlfn._xlws.FILTER(Main!A2:J{last_row}, Main!J2:J{last_row}="X", "No Scratches")'

        return output_path
