"""Unit and parity tests for the Rust `mm_core_rs` acceleration library."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from meet_validation import validate_meet_data
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.rust_bridge import (
    get_rust_lib,
    is_jet4_mdb_file,
    rust_convert_meet,
    rust_export_mdb_full_schema,
    rust_load_mdb_bundle,
    rust_validate_meet,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SINGERS_MDB = REPO_ROOT / "web-client" / "tests-e2e" / "Singers23.mdb"
CHAMPS_JSON = REPO_ROOT / "backend" / "src" / "data" / "sample_data_champs_2025-aftermeet.json"


@pytest.fixture(autouse=True)
def _enable_rust_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure Rust engine is enabled for direct Rust core unit tests."""
    monkeypatch.setenv("MM_ENGINE", "rust")
    monkeypatch.setenv("MM_DISABLE_RUST", "0")


def test_rust_lib_loads_and_identifies_jet4() -> None:
    """Verify the Rust dynamic library initializes and detects Jet 4.0 headers."""
    lib = get_rust_lib()
    assert lib is not None
    if SINGERS_MDB.exists():
        assert is_jet4_mdb_file(str(SINGERS_MDB)) is True


def test_rust_validate_meet_parity() -> None:
    """Verify Rust validation produces identical findings to the Python fallback."""
    if not CHAMPS_JSON.exists():
        return
    with open(CHAMPS_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    cache = raw.get("data", raw)

    rust_findings = validate_meet_data(cache)
    with patch.dict(os.environ, {"MM_DISABLE_RUST": "1"}):
        import mm_to_json.rust_bridge as rb

        rb._RUST_INIT_ATTEMPTED = False
        rb._RUST_LIB = None
        try:
            py_findings = validate_meet_data(cache)
        finally:
            rb._RUST_INIT_ATTEMPTED = False
            rb._RUST_LIB = None

    assert len(rust_findings) == len(py_findings)
    assert len(rust_findings) > 0
    for rf, pf in zip(rust_findings, py_findings, strict=True):
        assert rf.severity == pf.severity
        assert rf.category == pf.category
        assert rf.message == pf.message
        assert rf.affected_id == pf.affected_id


def test_rust_convert_meet_parity() -> None:
    """Verify Rust relational converter matches the Python converter output."""
    if not CHAMPS_JSON.exists():
        return
    with open(CHAMPS_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    table_data = raw.get("data", raw)

    rust_out = rust_convert_meet(table_data, from_mdb=False)
    assert rust_out is not None

    conv = MmToJsonConverter(table_data=table_data)
    # Force Python fallback by clearing fingerprint
    conv._tables_fingerprint = None
    py_out = conv.convert()

    assert rust_out["meetName"] == py_out["meetName"]
    assert len(rust_out["sessions"]) == len(py_out["sessions"])
    for rs, ps in zip(rust_out["sessions"], py_out["sessions"], strict=True):
        assert len(rs["events"]) == len(ps["events"])
        for re_evt, pe_evt in zip(rs["events"], ps["events"], strict=True):
            assert re_evt["eventNum"] == pe_evt["eventNum"]
            assert re_evt["eventDesc"] == pe_evt["eventDesc"]
            assert len(re_evt["entries"]) == len(pe_evt["entries"])


def test_rust_mdb_bundle_and_schema_export() -> None:
    """Verify Rust Jet 4.0 binary MDB parser loads Singers23.mdb accurately."""
    if not SINGERS_MDB.exists():
        return
    bundle = rust_load_mdb_bundle(str(SINGERS_MDB))
    assert bundle is not None
    assert bundle["schema_type"] == "B"
    assert len(bundle["tables"]["athlete"]) > 100
    assert len(bundle["converted"]["sessions"]) >= 1

    schema = rust_export_mdb_full_schema(str(SINGERS_MDB))
    assert schema is not None
    assert "tables" in schema
    assert len(schema["tables"]) == 50


def test_rust_bridge_refcount_stability() -> None:
    """Verify repeated calls across the CPython C-API bridge do not leak reference counts."""
    sample = {
        "team": [{"team_no": 1, "team_name": "Sharks", "team_abbr": "SHK", "team_lsc": "PC"}],
        "athlete": [
            {
                "ath_no": 10,
                "first_name": "Alex",
                "last_name": "Swimmer",
                "ath_sex": "M",
                "ath_age": 10,
                "team_no": 1,
            }
        ],
        "event": [
            {
                "event_ptr": 1,
                "event_no": 1,
                "event_sex": "M",
                "low_age": 9,
                "high_age": 10,
                "ind_rel": "I",
                "event_dist": 50,
                "event_stroke": "A",
            }
        ],
        "entry": [{"ath_no": 10, "event_ptr": 1, "fin_heat": 1, "fin_lane": 3, "fin_time": 32.50}],
    }
    base_refcnt = sys.getrefcount(sample)
    for _ in range(50):
        v_res = rust_validate_meet(sample)
        c_res = rust_convert_meet(sample, from_mdb=False)
        assert v_res is not None
        assert c_res is not None
    assert sys.getrefcount(sample) == base_refcnt


def test_tables_mutation_invalidates_rust_cache() -> None:
    """Verify mutating converter.tables invalidates cached Rust output."""
    sample = {
        "meet": [{"meet_name1": "Initial Meet"}],
        "event": [],
    }
    conv = MmToJsonConverter(table_data=sample)
    assert conv.convert()["meetName"] == "Initial Meet"

    conv.tables["meet"] = pd.DataFrame([{"meet_name1": "Updated Meet"}])
    assert conv.convert()["meetName"] == "Updated Meet"


def test_schema_b_table_data_and_overflow_safety() -> None:
    """Verify Schema B table_data with MTEVENT, duplicate-cased keys, and large ints work via py_bridge."""
    schema_b_data = {
        "MEET": [{"Meet": "Schema B Test Meet"}],
        "MTEVENT": [
            {
                "MtEvent": 1,
                "MtEv": 1,
                "Sex": "F",
                "Lo_Hi": 910,
                "Distance": 50,
                "Stroke": 1,
                "I_R": "I",
                "Session": 1,
            }
        ],
        "TEAM": [{"Team": 1, "TCode": "DP", "TName": "Del Prado"}],
        "ATHLETE": [
            {"Athlete": 100, "First": "Jane", "Last": "Doe", "Sex": "F", "Age": 10, "Team1": 1},
            {
                "Athlete": 101,
                "First_name": "ShouldBeOverridden",
                "first_name": "ActualName",
                "Last": "Smith",
                "Sex": "F",
                "Age": 10,
                "Team1": 1,
                "huge_unused_int": 10**30,
            },
        ],
        "ENTRY": [
            {"MtEvent": 1, "Athlete": 100, "Heat": 1, "Lane": 2, "Score": 3150},
            {"MtEvent": 1, "Athlete": 101, "Heat": 1, "Lane": 3, "Score": 3250},
        ],
    }
    res = rust_convert_meet(schema_b_data, from_mdb=False)
    assert res is not None
    assert len(res["sessions"]) == 1
    assert len(res["sessions"][0]["events"]) == 1
    entries = res["sessions"][0]["events"][0]["entries"]
    assert len(entries) == 2
    assert entries[1]["firstName"] == "ActualName"


def test_engine_configuration_toggle() -> None:
    """Verify MM_ENGINE=rust|python|java and MM_DISABLE_RUST=1 environment toggles."""
    from mm_to_json.rust_bridge import is_rust_engine_enabled

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("MM_ENGINE", None)
        os.environ.pop("MM_DISABLE_RUST", None)
        assert is_rust_engine_enabled() is True

    with patch.dict(os.environ, {"MM_ENGINE": "rust"}):
        assert is_rust_engine_enabled() is True

    with patch.dict(os.environ, {"MM_ENGINE": "python"}):
        assert is_rust_engine_enabled() is False
        assert get_rust_lib() is None

    with patch.dict(os.environ, {"MM_ENGINE": "java"}):
        assert is_rust_engine_enabled() is False

    with patch.dict(os.environ, {"MM_ENGINE": "rust", "MM_DISABLE_RUST": "1"}):
        assert is_rust_engine_enabled() is False
