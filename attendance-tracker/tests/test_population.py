import unittest
from unittest.mock import patch
import os
import sys

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from populate_sheets import apply_formatting, populate  # noqa: E402


class TestSpreadsheetPopulation(unittest.TestCase):
    def test_apply_formatting_requests(self):
        sheet_id = 12345
        row_count = 10
        requests = apply_formatting(sheet_id, row_count)

        # Verify column widths
        width_requests = [
            r
            for r in requests
            if "updateDimensionProperties" in r
            and r["updateDimensionProperties"]["properties"].get("pixelSize")
        ]
        self.assertEqual(len(width_requests), 13)  # 13 columns set

        # Verify hidden columns
        hide_requests = [
            r
            for r in requests
            if "updateDimensionProperties" in r
            and r["updateDimensionProperties"]["properties"].get("hiddenByUser")
        ]
        self.assertEqual(len(hide_requests), 1)
        self.assertEqual(
            hide_requests[0]["updateDimensionProperties"]["range"]["startIndex"], 13
        )

        # Verify frozen row
        freeze_requests = [r for r in requests if "updateSheetProperties" in r]
        self.assertEqual(len(freeze_requests), 1)
        self.assertEqual(
            freeze_requests[0]["updateSheetProperties"]["properties"]["gridProperties"][
                "frozenRowCount"
            ],
            1,
        )

        # Verify checkboxes
        checkbox_requests = [r for r in requests if "setDataValidation" in r]
        self.assertEqual(len(checkbox_requests), 1)
        self.assertEqual(
            checkbox_requests[0]["setDataValidation"]["range"]["endRowIndex"], 11
        )

    @patch("populate_sheets.os.path.exists")
    @patch("populate_sheets.run_gws")
    @patch(
        "builtins.open",
        unittest.mock.mock_open(
            read_data='[{"Last Name": "Smith", "Preferred Name": "Alice", "Gender": "F", "Age Group": "7-8", "Free": "X", "Back": "", "Breast": "", "Fly": "", "IM": "", "Free Relay": "", "Medley Relay": "", "ID": 101, "First Name": "Alice", "Age": 8, "Team": "DP"}]'
        ),
    )
    def test_populate_execution(self, mock_gws, mock_exists):
        # We need to mock swimmers data as well
        # The mock_open above handles the file read
        mock_exists.return_value = True

        populate()

        # Verify Main tab update
        mock_gws.assert_any_call(
            "sheets",
            "spreadsheets",
            "values",
            "update",
            params=unittest.mock.ANY,
            body=unittest.mock.ANY,
        )

        # Verify batchUpdate for formatting
        mock_gws.assert_any_call(
            "sheets",
            "spreadsheets",
            "batchUpdate",
            params=unittest.mock.ANY,
            body=unittest.mock.ANY,
        )


if __name__ == "__main__":
    unittest.main()
