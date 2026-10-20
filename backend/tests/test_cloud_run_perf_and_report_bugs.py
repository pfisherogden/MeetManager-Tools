from __future__ import annotations

import os
import sys
from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    try:
        from meetmanager.v1 import meet_manager_pb2 as pb2
    except ImportError:
        import meet_manager_pb2 as pb2
except ImportError:
    pytest.skip("Protos not generated, skipping tests", allow_module_level=True)

from handlers.dataset_uploader import upload_dataset
from handlers.report_handler import (
    _process_single_report_process,
    _run_bundle_generation_job,
)
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer


def _make_schema_b_normalized_tables() -> dict[str, list[dict]]:
    """Simulates a Schema B dataset after export_raw() where table keys are lowercase."""
    return {
        "meet": [{"meet": 1, "mname": "2026 League Meet", "start": "2026-07-11", "course": "Y"}],
        "team": [
            {"team": 1, "tcode": "DP", "tname": "Deer Park", "lsc": "CA"},
            {"team": 2, "tcode": "KS", "tname": "Knockout Sharks", "lsc": "CA"},
        ],
        "athlete": [
            {"athlete": 101, "team1": 1, "first": "Alice", "last": "Swimmer", "sex": "F", "age": 10},
            {"athlete": 102, "team1": 1, "first": "Bob", "last": "Racer", "sex": "M", "age": 9},
            {"athlete": 103, "team1": 2, "first": "Charlie", "last": "Dolphin", "sex": "M", "age": 10},
        ],
        "event": [
            {
                "mtevent": 1,
                "mt_no": 1,
                "low_age": 9,
                "high_Age": 10,
                "sex": "F",
                "ind_rel": "I",
                "distance": 50,
                "stroke": 1,
                "session": 1,
            },
            {
                "mtevent": 2,
                "mt_no": 2,
                "low_age": 9,
                "high_Age": 10,
                "sex": "M",
                "ind_rel": "I",
                "distance": 50,
                "stroke": 1,
                "session": 1,
            },
        ],
        "entry": [
            {"mtevent": 1, "athlete": 101, "team": 1, "convseed_time": 32.50, "heat": 1, "lane": 3},
            {"mtevent": 2, "athlete": 102, "team": 1, "convseed_time": 34.10, "heat": 1, "lane": 4},
            {"mtevent": 2, "athlete": 103, "team": 2, "convseed_time": 35.00, "heat": 1, "lane": 5},
        ],
        "relay": [],
        "relaynames": [],
        "splits": [],
        "session": [{"sess_no": 1, "sess_name": "Morning Session", "sess_day": 1, "sess_starttime": 32400}],
        " sessitem": [{"sess_ptr": 1, "event_ptr": 1, "sess_order": 1}],
        "divisions": [],
        "scoring": [],
    }


def test_issue_627_parent_entry_list_mixed_gender_and_schema_b():
    """Regression test for #627:
    - Schema B tables with lowercase normalized keys ('event', 'entry') must be detected as Schema B.
    - extract_meet_entries_data with gender_filter='Mixed' must NOT filter out M and F swimmers.
    - extract_meet_entries_data with team_filter='DP' must match 2-letter teamCode 'DP'.
    """
    raw_tables = _make_schema_b_normalized_tables()
    converter = MmToJsonConverter(table_data=raw_tables)
    assert converter.schema_type == "B"

    full_data = converter.convert()
    total_entries = sum(
        len(evt.get("entries", [])) for sess in full_data.get("sessions", []) for evt in sess.get("events", [])
    )
    assert total_entries == 3

    extractor = ReportDataExtractor(converter, full_data=full_data)

    # 1. Mixed gender filter (default in Report Pack Builder) must include M and F swimmers
    entries_mixed = extractor.extract_meet_entries_data(
        team_filter="",
        report_title="Parent Entry List",
        gender_filter="Mixed",
        age_group_filter="Open",
    )
    assert len(entries_mixed["groups"]) == 2
    dp_group = next(g for g in entries_mixed["groups"] if "Deer Park" in g["header"])
    assert len(dp_group["sub_items"]) == 2  # Alice (F) and Bob (M)

    # 2. 2-letter team code filter ('DP') must match Deer Park
    entries_dp = extractor.extract_meet_entries_data(
        team_filter="DP",
        report_title="Parent Entry List - DP Only",
        gender_filter="Mixed",
        age_group_filter="Open",
    )
    assert len(entries_dp["groups"]) == 1
    assert "Deer Park" in entries_dp["groups"][0]["header"]
    assert len(entries_dp["groups"][0]["sub_items"]) == 2


def test_issue_627_lineups_report_extracts_heats(tmp_path):
    """Regression test for #627: rtype='lineups' must use extract_meet_program_data so heats are populated."""
    raw_tables = _make_schema_b_normalized_tables()
    converter = MmToJsonConverter(table_data=raw_tables)
    full_data = converter.convert()
    extractor = ReportDataExtractor(converter, full_data=full_data)

    rtype_map = {pb2.REPORT_TYPE_LINEUPS: "lineups"}
    res = _process_single_report_process(
        pb2.REPORT_TYPE_LINEUPS,
        "Team Lineup Sheets",
        "",
        "Mixed",
        "Open",
        "dev-user",
        2,
        True,
        True,
        "",
        rtype_map,
        renderer_type=pb2.RENDERER_TYPE_WEASYPRINT,
        html_preview=True,
        idx=0,
        preloaded_extractor=extractor,
        preloaded_full_data=full_data,
    )
    assert res["success"] is True
    assert "Heat 1 of 1 Finals" in res["html_content"]
    assert "Swimmer, Alice" in res["html_content"]


def test_issue_628_zebra_striping_rendered_across_templates(tmp_path):
    """Regression test for #628: zebra_striping=True applies .zebra-row and visible #e8ecf2 shading."""
    raw_tables = _make_schema_b_normalized_tables()
    converter = MmToJsonConverter(table_data=raw_tables)
    full_data = converter.convert()
    extractor = ReportDataExtractor(converter, full_data=full_data)

    renderer = WeasyRenderer(output_path=str(tmp_path / "out.pdf"))

    # 1. Entries (HY-TEK style)
    entries_data = extractor.extract_meet_entries_data(gender_filter="Mixed")
    entries_data["zebra_striping"] = True
    html_hytek = renderer.render_to_html(entries_data, "entries_hytek.j2")
    assert "zebra-row" in html_hytek
    assert "#e8ecf2" in html_hytek

    # 2. Entries (Club style)
    html_club = renderer.render_to_html(entries_data, "entries_club.j2")
    assert "zebra-row" in html_club
    assert "#e8ecf2" in html_club

    # 3. Lane Timer Sheets
    timer_data = extractor.extract_lane_timer_sheets_data(gender_filter="Mixed")
    timer_data["zebra_striping"] = True
    html_timer = renderer.render_to_html(timer_data, "timer_sheets.j2")
    assert "zebra-row" in html_timer
    assert "#e8ecf2" in html_timer


def test_issue_626_bundle_generation_uses_in_memory_threads_with_weasy_rs(tmp_path, monkeypatch):
    """Regression test for #626: _run_bundle_generation_job skips msgpack disk serialization when weasy-rs is active."""
    monkeypatch.setenv("MM_ENGINE", "rust")
    monkeypatch.setenv("MM_PDF_ENGINE", "rust")
    monkeypatch.delenv("MM_DISABLE_RUST", raising=False)
    raw_tables = _make_schema_b_normalized_tables()

    servicer = MagicMock()
    servicer.storage.get_url.return_value = "/api/data?path=bundle.zip"

    req = pb2.GenerateReportBundleRequest(
        reports=[
            pb2.GenerateReportRequest(
                type=pb2.REPORT_TYPE_ENTRIES,
                title="Parent Entry List",
                gender_filter="Mixed",
                zebra_striping=True,
            ),
            pb2.GenerateReportRequest(
                type=pb2.REPORT_TYPE_MEET_PROGRAM,
                title="Meet Program",
                gender_filter="Mixed",
                zebra_striping=True,
            ),
        ],
        bundle_name="fast_pack.zip",
        renderer_type=pb2.RENDERER_TYPE_WEASYPRINT,
    )

    with patch("handlers.report_handler.msgpack.pack") as mock_msgpack_pack:
        res = _run_bundle_generation_job("job-626", req, "user-1", raw_tables, servicer, pb2)
        assert res["success"] is True
        # With weasy-rs enabled, msgpack.pack should not be called at all
        mock_msgpack_pack.assert_not_called()


def test_issue_625_export_raw_fast_path_and_upload_populates_cache(tmp_path):
    """Regression test for #625:
    - export_raw() returns _raw_tables_dict directly without calling DataFrame.to_dict.
    - upload_dataset populates servicer._user_cache[uid] immediately.
    """
    raw_tables = _make_schema_b_normalized_tables()
    converter = MmToJsonConverter(table_data=raw_tables)
    converter._raw_tables_dict = raw_tables

    with patch.object(pd.DataFrame, "to_dict") as mock_to_dict:
        exported = converter.export_raw()
        assert exported["athlete"] == raw_tables["athlete"]
        assert exported["team"] == raw_tables["team"]
        mock_to_dict.assert_not_called()

    # Verify upload_dataset pre-populates _user_cache
    servicer = MagicMock()
    servicer._user_cache = OrderedDict()
    servicer._check_auth.return_value = "prod-user-123"
    servicer._get_user_config_path.return_value = "users/prod-user-123/config.json"
    servicer._load_user_config.return_value = {}
    servicer._load_mdb.return_value = raw_tables

    chunks = [
        pb2.UploadDatasetRequest(filename="test_meet.mdb"),
        pb2.UploadDatasetRequest(chunk=b"dummy-mdb-bytes"),
    ]
    resp = upload_dataset(iter(chunks), MagicMock(), servicer, pb2)
    assert resp.success is True
    assert "prod-user-123" in servicer._user_cache
    assert servicer._user_cache["prod-user-123"]["data"] == raw_tables
    assert servicer._user_cache["prod-user-123"]["filename"] == "test_meet.mdb"
    assert servicer._user_cache["prod-user-123"]["config"]["active_dataset"] == "test_meet.mdb"
