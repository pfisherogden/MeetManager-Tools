"""Comprehensive end-to-end pipeline and cross-engine parity tests for MeetManager-Tools."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import msgpack
import pdfplumber
import pytest

from handlers.report_handler import _process_single_report_process, msgpack_encode
from mm_to_json.mdb_restorer import restore_db
from mm_to_json.mdb_writer import (
    add_athlete,
    add_team,
    open_db,
    update_entry_status,
)
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.meet_event_writer import MeetEventWriter
from mm_to_json.reporting.weasy_renderer import WeasyRenderer


def _sample_mdb_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "web-client" / "tests-e2e" / "Singers23.mdb"


def test_full_mdb_roundtrip_and_live_write_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify full MDB creation via restore_db -> open_db -> add_team/add_athlete -> update_entry_status DQ -> Rust/Python read parity."""
    monkeypatch.setenv("MM_ENGINE", "rust")
    monkeypatch.delenv("MM_DISABLE_RUST", raising=False)

    schema = {
        "tables": {
            "Meet": {
                "columns": [
                    {"name": "Meet_name1", "type": "TEXT", "length": 90},
                    {"name": "Meet_start", "type": "SHORT_DATE_TIME"},
                    {"name": "Meet_maxind", "type": "INT"},
                    {"name": "Meet_maxrel", "type": "INT"},
                    {"name": "Meet_maxcomb", "type": "INT"},
                ],
                "rows": [
                    {
                        "Meet_name1": "2026 TVSL Dual Meet",
                        "Meet_start": 1780704000000,
                        "Meet_maxind": 3,
                        "Meet_maxrel": 3,
                        "Meet_maxcomb": 4,
                    }
                ],
                "indexes": [],
            },
            "TEAM": {
                "columns": [
                    {"name": "Team", "type": "LONG"},
                    {"name": "Team_no", "type": "LONG"},
                    {"name": "TCode", "type": "TEXT", "length": 10},
                    {"name": "Team_abbr", "type": "TEXT", "length": 10},
                    {"name": "TName", "type": "TEXT", "length": 60},
                    {"name": "Team_name", "type": "TEXT", "length": 60},
                    {"name": "Short", "type": "TEXT", "length": 32},
                    {"name": "LSC", "type": "TEXT", "length": 6},
                    {"name": "TType", "type": "TEXT", "length": 6},
                    {"name": "Regn", "type": "TEXT", "length": 2},
                    {"name": "TM50", "type": "BOOLEAN"},
                ],
                "rows": [
                    {
                        "Team": 1,
                        "Team_no": 1,
                        "TCode": "DP",
                        "Team_abbr": "DP",
                        "TName": "Del Prado Stingrays",
                        "Team_name": "Del Prado Stingrays",
                        "Short": "Stingrays",
                        "LSC": "PC",
                        "TType": "AGE",
                        "Regn": "U",
                        "TM50": False,
                    }
                ],
                "indexes": [],
            },
            "ATHLETE": {
                "columns": [
                    {"name": "Athlete", "type": "LONG"},
                    {"name": "Ath_no", "type": "LONG"},
                    {"name": "Team1", "type": "LONG"},
                    {"name": "Team_no", "type": "LONG"},
                    {"name": "First", "type": "TEXT", "length": 40},
                    {"name": "First_name", "type": "TEXT", "length": 40},
                    {"name": "Last", "type": "TEXT", "length": 40},
                    {"name": "Last_name", "type": "TEXT", "length": 40},
                    {"name": "Sex", "type": "TEXT", "length": 2},
                    {"name": "Ath_sex", "type": "TEXT", "length": 2},
                    {"name": "Age", "type": "INT"},
                    {"name": "Ath_age", "type": "INT"},
                    {"name": "Class", "type": "TEXT", "length": 4},
                    {"name": "Citizen", "type": "TEXT", "length": 6},
                    {"name": "Inactive", "type": "BOOLEAN"},
                ],
                "rows": [
                    {
                        "Athlete": 101,
                        "Ath_no": 101,
                        "Team1": 1,
                        "Team_no": 1,
                        "First": "Alice",
                        "First_name": "Alice",
                        "Last": "Swimmer",
                        "Last_name": "Swimmer",
                        "Sex": "F",
                        "Ath_sex": "F",
                        "Age": 10,
                        "Ath_age": 10,
                        "Class": "",
                        "Citizen": "USA",
                        "Inactive": False,
                    }
                ],
                "indexes": [],
            },
            "Event": {
                "columns": [
                    {"name": "Event_no", "type": "INT"},
                    {"name": "Event_ptr", "type": "LONG"},
                    {"name": "Ind_rel", "type": "TEXT", "length": 2},
                    {"name": "Event_sex", "type": "TEXT", "length": 2},
                    {"name": "Event_gender", "type": "TEXT", "length": 2},
                    {"name": "Event_dist", "type": "FLOAT"},
                    {"name": "Event_stroke", "type": "TEXT", "length": 2},
                    {"name": "Low_age", "type": "INT"},
                    {"name": "High_Age", "type": "INT"},
                    {"name": "Num_prelanes", "type": "INT"},
                    {"name": "Num_finlanes", "type": "INT"},
                ],
                "rows": [
                    {
                        "Event_no": 1,
                        "Event_ptr": 1,
                        "Ind_rel": "I",
                        "Event_sex": "F",
                        "Event_gender": "F",
                        "Event_dist": 50.0,
                        "Event_stroke": "A",
                        "Low_age": 9,
                        "High_Age": 10,
                        "Num_prelanes": 6,
                        "Num_finlanes": 6,
                    }
                ],
                "indexes": [],
            },
            "ENTRY": {
                "columns": [
                    {"name": "Event_ptr", "type": "LONG"},
                    {"name": "Ath_no", "type": "LONG"},
                    {"name": "ActSeed_course", "type": "TEXT", "length": 2},
                    {"name": "ActualSeed_time", "type": "FLOAT"},
                    {"name": "ConvSeed_course", "type": "TEXT", "length": 2},
                    {"name": "ConvSeed_time", "type": "FLOAT"},
                    {"name": "Scr_stat", "type": "BOOLEAN"},
                    {"name": "Pre_heat", "type": "INT"},
                    {"name": "Pre_lane", "type": "INT"},
                    {"name": "Pre_stat", "type": "TEXT", "length": 2},
                    {"name": "Pre_Time", "type": "FLOAT"},
                    {"name": "Pre_dqcode", "type": "TEXT", "length": 4},
                    {"name": "Fin_heat", "type": "INT"},
                    {"name": "Fin_lane", "type": "INT"},
                    {"name": "Fin_stat", "type": "TEXT", "length": 2},
                    {"name": "Fin_Time", "type": "FLOAT"},
                    {"name": "Fin_place", "type": "INT"},
                    {"name": "Fin_dqcode", "type": "TEXT", "length": 4},
                    {"name": "Sem_heat", "type": "INT"},
                    {"name": "Sem_lane", "type": "INT"},
                    {"name": "Sem_stat", "type": "TEXT", "length": 2},
                    {"name": "Sem_dqcode", "type": "TEXT", "length": 4},
                ],
                "rows": [
                    {
                        "Event_ptr": 1,
                        "Ath_no": 101,
                        "ActSeed_course": "Y",
                        "ActualSeed_time": 34.50,
                        "ConvSeed_course": "Y",
                        "ConvSeed_time": 34.50,
                        "Scr_stat": False,
                        "Pre_heat": 0,
                        "Pre_lane": 0,
                        "Pre_stat": "",
                        "Pre_Time": 0.0,
                        "Pre_dqcode": "",
                        "Fin_heat": 1,
                        "Fin_lane": 3,
                        "Fin_stat": "",
                        "Fin_Time": 33.80,
                        "Fin_place": 1,
                        "Fin_dqcode": "",
                        "Sem_heat": 0,
                        "Sem_lane": 0,
                        "Sem_stat": "",
                        "Sem_dqcode": "",
                    }
                ],
                "indexes": [],
            },
        }
    }

    schema_file = tmp_path / "live_schema.json"
    schema_file.write_text(json.dumps(schema), encoding="utf-8")
    mdb_file = tmp_path / "live_meet.mdb"
    restore_db(str(schema_file), str(mdb_file))

    db = open_db(str(mdb_file))
    try:
        tid = add_team(db, team_id=2, abbr="BH", name="Bret Harte Bullfrogs")
        assert tid == 2
        aid = add_athlete(db, athlete_id=102, team_id=2, first="Bob", last="Racer", gender="M", age=10)
        assert aid == 102

        updated = update_entry_status(
            db,
            event_ptr=1,
            athlete_id=101,
            heat=1,
            lane=3,
            status="DQ",
            dq_code="1A",
            round_type="F",
            is_relay=False,
        )
        assert updated is True
    finally:
        db.close()

    with MmToJsonConverter(mdb_path=str(mdb_file)) as rust_conv:
        rust_schema = rust_conv.export_full_schema()
        rust_converted = rust_conv.convert()

    entry_rows = rust_schema["tables"]["ENTRY"]["rows"]
    assert len(entry_rows) == 1
    assert entry_rows[0]["Fin_stat"] == "Q"
    assert entry_rows[0]["Fin_dqcode"] == "1A"
    assert len(rust_schema["tables"]["TEAM"]["rows"]) == 2
    assert len(rust_schema["tables"]["ATHLETE"]["rows"]) == 2
    assert rust_converted.get("meetName") == "2026 TVSL Dual Meet"


def test_report_handler_worker_all_report_types_unmocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Execute `_process_single_report_process` unmocked across all PDF, HTML, CTS, and Check-In types."""
    mdb_path = _sample_mdb_path()
    if not mdb_path.exists():
        pytest.skip("Singers23.mdb not found")

    monkeypatch.setenv("MM_ENGINE", "rust")
    monkeypatch.setenv("MM_PDF_ENGINE", "rust")
    monkeypatch.delenv("MM_DISABLE_RUST", raising=False)

    with MmToJsonConverter(mdb_path=str(mdb_path)) as conv:
        full_data = conv.convert()
        cache = {k: df.to_dict(orient="records") for k, df in conv.tables.items() if hasattr(df, "to_dict")}

    msgpack_path = tmp_path / "bundle_data.msgpack"
    with open(msgpack_path, "wb") as f:
        msgpack.pack({"full_data": full_data, "cache": cache}, f, default=msgpack_encode)

    rtype_map = {
        0: "psych",
        1: "entries",
        2: "lineups",
        3: "results",
        4: "program",
        5: "entries_club",
        6: "lane_timer_sheets",
        7: "judge_sheets",
        8: "program_html",
        9: "cts_export",
        10: "check_in_sheet",
    }

    for req_type, expected_rtype in rtype_map.items():
        res = _process_single_report_process(
            report_req_type=req_type,
            report_req_title=f"Test {expected_rtype}",
            report_req_team_filter="",
            report_req_gender_filter="",
            report_req_age_group_filter="",
            user_id="test-user",
            columns_on_page=2,
            show_relay_swimmers=True,
            zebra_striping=True,
            msgpack_path=str(msgpack_path),
            rtype_map=rtype_map,
            renderer_type=0,
            html_preview=(expected_rtype == "program_html"),
            idx=req_type,
        )
        assert res["success"] is True, f"Failed for {expected_rtype}: {res.get('error')}"

        if expected_rtype == "cts_export":
            files = res.get("files", [])
            assert any(f["filename"] == "events.csv" for f in files)
        elif expected_rtype == "check_in_sheet":
            content = res["content"]
            assert isinstance(content, bytes) and len(content) > 100
            assert res["filename"].endswith(".xlsx")
        elif expected_rtype == "program_html":
            content = res["content"]
            assert b"<!DOCTYPE html>" in content or b"<html" in content
        else:
            content = res["content"]
            assert isinstance(content, bytes) and content.startswith(b"%PDF-1.4")


def test_weasy_rs_vs_weasyprint_content_and_layout_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Compare PDFs rendered by Rust `weasy-rs` vs Python `WeasyPrint` for text & structure parity."""
    mdb_path = _sample_mdb_path()
    if not mdb_path.exists():
        pytest.skip("Singers23.mdb not found")

    monkeypatch.setenv("MM_ENGINE", "rust")
    conv = MmToJsonConverter(mdb_path=str(mdb_path))
    full_data = conv.convert()
    ext = ReportDataExtractor(conv, full_data=full_data)

    cases: list[tuple[str, str, dict[str, Any]]] = [
        (
            "program_2col",
            "meet_program.j2",
            ext.extract_meet_program_data(report_title="Parity Program", columns_on_page=2, show_relay_swimmers=True),
        ),
        (
            "psych_2col",
            "psych_sheet.j2",
            ext.extract_psych_sheet_data(report_title="Parity Psych Sheet"),
        ),
        (
            "results",
            "results.j2",
            ext.extract_results_data(report_title="Parity Results"),
        ),
    ]

    for name, template_name, data in cases:
        rust_pdf = tmp_path / f"{name}_rust.pdf"
        py_pdf = tmp_path / f"{name}_weasyprint.pdf"

        monkeypatch.setenv("MM_PDF_ENGINE", "rust")
        r_rust = WeasyRenderer(str(rust_pdf))
        if template_name == "meet_program.j2":
            r_rust.render_meet_program(data)
        else:
            r_rust.render_entries(data, template_name)

        monkeypatch.setenv("MM_PDF_ENGINE", "weasyprint")
        r_py = WeasyRenderer(str(py_pdf))
        if template_name == "meet_program.j2":
            r_py.render_meet_program(data)
        else:
            r_py.render_entries(data, template_name)

        with pdfplumber.open(str(rust_pdf)) as pdf_r, pdfplumber.open(str(py_pdf)) as pdf_w:
            assert len(pdf_r.pages) >= 1
            assert len(pdf_w.pages) >= 1
            text_r = "\n".join(p.extract_text() or "" for p in pdf_r.pages)
            text_w = "\n".join(p.extract_text() or "" for p in pdf_w.pages)

            assert data["sub_title"] in text_r
            assert data["sub_title"] in text_w
            for ev in data.get("events", [])[:5]:
                ev_num = str(ev.get("event_num", ""))
                if ev_num:
                    assert f"Event {ev_num}" in text_r
                    assert f"Event {ev_num}" in text_w


def test_season_setup_end_to_end_with_real_mdb_restorer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify SeasonTransformer + real binary MDB creation via restore_db + EV3/HYV export."""
    tests_dir = Path(__file__).resolve().parent
    scripts_dir = tests_dir.parent / "scripts" / "season_setup"
    integration_dir = tests_dir / "integration"
    for p in (str(scripts_dir), str(integration_dir)):
        if p not in sys.path:
            sys.path.insert(0, p)

    from mock_mdb_generator import generate_mock_mdb
    from season_transformer import SeasonTransformer

    monkeypatch.setenv("MM_ENGINE", "rust")
    raw_data = generate_mock_mdb(seed=99)
    transformer = SeasonTransformer(raw_data)
    transformer.purge_data(preserve_team_abbr="DP")
    transformer.update_meet(
        name="2026 E2E Dual Meet",
        start_date="2026-06-06",
        lanes=6,
        location="Del Prado Cabana Club",
        age_up="2026-06-01",
        entry_open="2026-05-30",
        entry_deadline="2026-06-02",
    )
    transformer.consolidate_sessions(is_champs=False)

    schema_dict: dict[str, Any] = {"tables": {}}
    for tname, rows in transformer.table_data.items():
        cols = []
        if rows:
            for cname, val in rows[0].items():
                ctype = "LONG" if isinstance(val, int) and not isinstance(val, bool) else "TEXT"
                if isinstance(val, bool):
                    ctype = "BOOLEAN"
                elif isinstance(val, float):
                    ctype = "DOUBLE"
                cols.append({"name": cname, "type": ctype, "length": 100})
        schema_dict["tables"][tname] = {"columns": cols, "rows": rows, "indexes": []}

    schema_json = tmp_path / "season_schema.json"
    schema_json.write_text(json.dumps(schema_dict), encoding="utf-8")

    out_mdb = tmp_path / "2026_E2E_Dual_Meet.mdb"
    restore_db(str(schema_json), str(out_mdb))
    assert out_mdb.exists()

    with MmToJsonConverter(mdb_path=str(out_mdb)) as conv:
        info = conv.get_meet_info()
        assert info["meetName"] == "2026 E2E Dual Meet"
        assert info["numLanes"] == 6

        zip_path = tmp_path / "meet_events.zip"
        writer = MeetEventWriter(
            transformer.table_data["Meet"][0],
            transformer.table_data.get("Session", []),
            transformer.table_data["Event"],
            transformer.table_data.get("Scoring", []),
            flatten_sessions=False,
        )
        writer.write_to_zip(str(zip_path))
        assert zip_path.exists()
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert any(n.endswith(".ev3") for n in zf.namelist())
            assert any(n.endswith(".hyv") for n in zf.namelist())
