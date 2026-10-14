"""Unit tests for live result syncing from timing systems (Issue #168)."""

import json
import os
from collections import OrderedDict
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from handlers.live_result_handler import (
    apply_live_results_to_cache,
    parse_time_value,
    parse_timing_result_chunk,
    upload_result_chunk,
)
from meetmanager.v1 import meet_manager_pb2 as pb2
from mm_to_json.live_result_watcher import TimingResultWatcher


class _DummyStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def exists(self, path: str) -> bool:
        return path in self.files

    def upload_file(self, src_path: str, dest_path: str) -> None:
        with open(src_path, "rb") as f:
            self.files[dest_path] = f.read()

    def download_file(self, src_path: str, dest_path: str) -> None:
        with open(dest_path, "wb") as f:
            f.write(self.files[src_path])


class _DummyServicer:
    def __init__(self, cache: dict[str, Any]) -> None:
        self.storage = _DummyStorage()
        self._user_cache: OrderedDict[str, dict[str, Any]] = OrderedDict(
            {"user-1": {"filename": "Meet.json", "mtime": 1, "data": cache}}
        )
        self._cache = cache

    def _check_auth(self, context: Any) -> str:
        return "user-1"

    def _load_user_config(self, context: Any) -> dict[str, Any]:
        return {"active_dataset": "Meet.json"}

    def _load_user_data(self, context: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._cache, {"active_dataset": "Meet.json"}

    def _get_table(self, cache: dict[str, Any], name: str) -> list[dict[str, Any]]:
        return cache.get(name, [])

    def _get_field(self, d: dict[str, Any], keys: list[str], default: Any = None) -> Any:
        for k in keys:
            if k in d:
                return d[k]
            for actual_k, val in d.items():
                if actual_k.lower() == k.lower():
                    return val
        return default

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _mask_uid(self, uid: str) -> str:
        return "***"

    def _mask_path(self, path: str) -> str:
        return path


def test_parse_time_value_formats() -> None:
    """Verify time strings, numeric seconds, and status codes are parsed accurately."""
    assert parse_time_value("28.45") == (28.45, "")
    assert parse_time_value("1:02.34") == (62.34, "")
    assert parse_time_value(31.2) == (31.2, "")
    assert parse_time_value("DQ") == (None, "DQ")
    assert parse_time_value("NS") == (None, "NS")
    assert parse_time_value("SCR") == (None, "SCR")


def test_parse_timing_result_chunk_json_csv_and_cts() -> None:
    """Verify JSON, headered CSV, and semicolon-delimited CTS/Dolphin timing formats."""
    json_bytes = json.dumps([{"event": 1, "heat": 2, "lane": 4, "time": "1:05.12", "place": 1}]).encode("utf-8")
    parsed_json = parse_timing_result_chunk("E001.json", json_bytes)
    assert len(parsed_json) == 1
    assert parsed_json[0]["event"] == 1
    assert parsed_json[0]["heat"] == 2
    assert parsed_json[0]["lane"] == 4
    assert parsed_json[0]["time"] == 65.12
    assert parsed_json[0]["place"] == 1

    csv_bytes = b"event,heat,lane,time,place,status\n3,1,2,29.88,2,\n3,1,3,DQ,0,DQ\n"
    parsed_csv = parse_timing_result_chunk("results.csv", csv_bytes)
    assert len(parsed_csv) == 2
    assert parsed_csv[0]["time"] == 29.88
    assert parsed_csv[1]["status"] == "DQ"

    cts_bytes = b"5;1;4;24.19;1\n5;1;2;24.55;2\n"
    parsed_cts = parse_timing_result_chunk("E005H01.do4", cts_bytes)
    assert len(parsed_cts) == 2
    assert parsed_cts[0] == {"event": 5, "heat": 1, "lane": 4, "time": 24.19, "place": 1, "status": ""}


def test_upload_result_chunk_updates_cache_and_persists() -> None:
    """Verify UploadResultChunk updates entries/relays via event_no->event_ptr mapping and persists."""
    sample_cache: dict[str, Any] = {
        "event": [{"event_no": 10, "event_ptr": 100}],
        "entry": [
            {
                "event_ptr": 100,
                "Ath_no": 42,
                "Fin_heat": 1,
                "Fin_lane": 3,
                "Fin_time": 0.0,
                "Fin_place": 0,
                "Fin_stat": "",
            }
        ],
        "relay": [],
    }
    servicer = _DummyServicer(sample_cache)
    req = pb2.UploadResultChunkRequest(
        filename="E010H01.csv",
        content=b"10,1,3,32.15,1\n",
        uid="user-1",
        access_token="mmtools-default-secret-2024",
    )
    resp = upload_result_chunk(req, MagicMock(), servicer, pb2)
    assert resp.success is True
    assert resp.updated_count == 1
    assert sample_cache["entry"][0]["Fin_time"] == 32.15
    assert sample_cache["entry"][0]["Fin_place"] == 1
    assert os.path.join("users", "user-1", "live", "synced_live_results.json") in servicer.storage.files


def test_timing_result_watcher_scans_new_and_modified_files(tmp_path: Path) -> None:
    """Verify TimingResultWatcher ingests new files once and re-ingests modified files."""
    seen: list[tuple[str, bytes]] = []
    watcher = TimingResultWatcher(tmp_path, on_chunk=lambda name, data: seen.append((name, data)))

    f1 = tmp_path / "E001H01.do4"
    f1.write_bytes(b"1;1;4;25.01;1\n")

    assert watcher.scan_once() == 1
    assert len(seen) == 1
    assert seen[0][0] == "E001H01.do4"

    # Unchanged file is not re-ingested
    assert watcher.scan_once() == 0
    assert len(seen) == 1

    # Modified file with different size/mtime is re-ingested
    f1.write_bytes(b"1;1;4;25.01;1\n1;1;2;25.44;2\n")
    assert watcher.scan_once() == 1
    assert len(seen) == 2
    assert apply_live_results_to_cache({}, [], _DummyServicer({})) == 0
