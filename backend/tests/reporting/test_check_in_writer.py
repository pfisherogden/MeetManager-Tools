from unittest.mock import MagicMock, patch

import gspread
import pytest

from mm_to_json.reporting.check_in_writer import SwimmerCheckInWriter, _cleanup_old_sheets


def _make_quota_api_error() -> gspread.exceptions.APIError:
    """Creates a realistic gspread APIError for 403 Drive storage quota exhaustion."""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.json.return_value = {
        "error": {
            "code": 403,
            "message": "The user's Drive storage quota has been exceeded.",
            "errors": [{"reason": "storageQuotaExceeded"}],
        }
    }
    mock_resp.text = "The user's Drive storage quota has been exceeded."
    return gspread.exceptions.APIError(mock_resp)


def test_cleanup_old_sheets_case_insensitive_and_trash_emptying():
    """Verifies _cleanup_old_sheets empties Drive trash and matches all check-in naming variants."""
    mock_gc = MagicMock()
    mock_gc.list_spreadsheet_files.return_value = [
        {"id": "id_1", "name": "Swimmer Check-in - 2026-06-01 08:00"},
        {"id": "id_2", "name": "Check-In Sheet - 2026-06-02 08:00"},
        {"id": "id_3", "name": "Attendance Tracker - 2026-06-03 08:00"},
        {"id": "id_4", "name": " - 2026-06-04 08:00"},
        {"id": "id_5", "name": "Custom Meet Name", "createdTime": "2026-06-05T08:00:00.000Z"},
        {"id": "id_unrelated", "name": "Season Budget Spreadsheet"},
    ]

    _cleanup_old_sheets(mock_gc, max_keep=2, current_title="Custom Meet Name")

    mock_gc.http_client.request.assert_called_once_with("delete", "https://www.googleapis.com/drive/v3/files/trash")
    deleted_ids = [call.args[0] for call in mock_gc.del_spreadsheet.call_args_list]
    # Should keep the 2 newest (id_4 and id_5) and delete the 3 older matched ones (id_1, id_2, id_3),
    # while leaving id_unrelated untouched.
    assert deleted_ids == ["id_1", "id_2", "id_3"]


def test_cleanup_old_sheets_max_keep_zero_deletes_all():
    """Verifies max_keep=0 deletes all target files (avoiding the [:-0] slice trap)."""
    mock_gc = MagicMock()
    mock_gc.list_spreadsheet_files.return_value = [
        {"id": "id_1", "name": "Swimmer Check-in - 2026-06-01 08:00"},
        {"id": "id_2", "name": "Other Owned Sheet", "createdTime": "2026-06-02T09:00:00.000Z"},
    ]

    _cleanup_old_sheets(mock_gc, max_keep=0, include_all_owned=True)

    deleted_ids = [call.args[0] for call in mock_gc.del_spreadsheet.call_args_list]
    assert deleted_ids == ["id_1", "id_2"]


def test_generate_google_sheet_retries_on_quota_exceeded():
    """Verifies generate_google_sheet performs aggressive cleanup and retries when gc.create hits 403 quota error."""
    writer = SwimmerCheckInWriter(
        [
            {
                "Last Name": "Smith",
                "Preferred Name": "Alex",
                "Gender": "M",
                "Age Group": "9-10",
            }
        ],
        title="",
    )
    # Empty title should default to "Swimmer Check-in"
    assert writer.title == "Swimmer Check-in"

    mock_gc = MagicMock()
    mock_gc.list_spreadsheet_files.return_value = [
        {"id": f"old_{i}", "name": f"Swimmer Check-in - 2026-06-01 08:{i:02d}"} for i in range(5)
    ]

    mock_sheet = MagicMock()
    mock_sheet.id = "new_sheet_id"
    mock_sheet.url = "https://docs.google.com/spreadsheets/d/new_sheet_id"
    mock_sheet.sheet1 = MagicMock()
    mock_sheet.sheet1.id = 0
    mock_ws = MagicMock()
    mock_ws.id = 1
    mock_sheet.add_worksheet.return_value = mock_ws

    # First create() fails with 403 quota exceeded, second succeeds after aggressive cleanup
    mock_gc.create.side_effect = [_make_quota_api_error(), mock_sheet]

    with (
        patch("mm_to_json.reporting.check_in_writer.default", return_value=(MagicMock(), "proj")),
        patch("mm_to_json.reporting.check_in_writer.gspread.authorize", return_value=mock_gc),
        patch.object(writer, "_install_apps_script"),
    ):
        url = writer.generate_google_sheet(user_email="coach@example.com")

    assert url == "https://docs.google.com/spreadsheets/d/new_sheet_id"
    assert mock_gc.create.call_count == 2
    # Aggressive retry cleanup with max_keep=0 should have deleted all 5 old sheets
    deleted_ids = [call.args[0] for call in mock_gc.del_spreadsheet.call_args_list]
    assert deleted_ids == ["old_0", "old_1", "old_2", "old_3", "old_4"]


def test_generate_google_sheet_reraises_non_quota_api_error():
    """Verifies non-quota APIErrors are not swallowed."""
    writer = SwimmerCheckInWriter([], title="Swimmer Check-in")
    mock_gc = MagicMock()
    mock_gc.list_spreadsheet_files.return_value = []

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = {"error": {"code": 500, "message": "Internal error"}}
    mock_resp.text = "Internal error"
    mock_gc.create.side_effect = gspread.exceptions.APIError(mock_resp)

    with (
        patch("mm_to_json.reporting.check_in_writer.default", return_value=(MagicMock(), "proj")),
        patch("mm_to_json.reporting.check_in_writer.gspread.authorize", return_value=mock_gc),
    ):
        with pytest.raises(gspread.exceptions.APIError):
            writer.generate_google_sheet()
    assert mock_gc.create.call_count == 1
