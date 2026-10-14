"""Handler and parser for incremental live timing system result chunks (Issue #168)."""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import tempfile
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Protocol

import grpc

if TYPE_CHECKING:
    from storage_provider import StorageProvider

LIVE_RESULTS_REL_PATH = os.path.join("live", "synced_live_results.json")


class LiveResultServicerContext(Protocol):
    """Protocol defining the servicer methods required by live_result_handler."""

    storage: StorageProvider
    _user_cache: OrderedDict[str, dict[str, Any]]

    def _check_auth(self, context: grpc.ServicerContext) -> str: ...
    def _load_user_config(self, context: grpc.ServicerContext) -> dict[str, Any]: ...
    def _load_user_data(self, context: grpc.ServicerContext) -> tuple[dict[str, Any], dict[str, Any]]: ...
    def _get_table(self, cache: dict[str, Any], name: str) -> list[dict[str, Any]]: ...
    def _get_field(self, d: dict[str, Any], keys: list[str], default: Any = None) -> Any: ...
    def _safe_int(self, value: Any, default: int = 0) -> int: ...
    def _mask_uid(self, uid: str) -> str: ...
    def _mask_path(self, path: str) -> str: ...


def parse_time_value(raw_time: Any) -> tuple[float | None, str]:
    """Parse a timing system time value into (seconds_float, status_code).

    Supports:
    - Float/int seconds (e.g. ``28.45``)
    - Formatted time strings (``"1:02.34"`` -> ``62.34``, ``"28.45"`` -> ``28.45``)
    - Status strings (``"DQ"``, ``"Q"``, ``"NS"``, ``"SCR"``, ``"R"``, ``"NT"``)
    """
    if raw_time is None:
        return None, ""
    if isinstance(raw_time, (int, float)):
        val = float(raw_time)
        return (val if val > 0 else None), ""

    text = str(raw_time).strip()
    if not text:
        return None, ""

    upper = text.upper()
    if upper in ("DQ", "Q", "DISQ"):
        return None, "DQ"
    if upper in ("NS", "NOSHOW", "DFS"):
        return None, "NS"
    if upper in ("SCR", "R"):
        return None, "SCR"
    if upper in ("NT", "DNF", "-"):
        return None, ""

    try:
        if ":" in text:
            parts = text.split(":")
            if len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                total = round(minutes * 60.0 + seconds, 2)
                return (total if total > 0 else None), ""
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                total = round(hours * 3600.0 + minutes * 60.0 + seconds, 2)
                return (total if total > 0 else None), ""
        total = round(float(text), 2)
        return (total if total > 0 else None), ""
    except ValueError:
        return None, ""


def _normalize_result_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a raw result dictionary into canonical keys."""

    def _lookup(keys: list[str]) -> Any:
        for k in keys:
            if k in item:
                return item[k]
            lower_k = k.lower()
            for actual_k, val in item.items():
                if actual_k.lower().strip() == lower_k:
                    return val
        return None

    raw_event = _lookup(["event", "event_no", "event_num", "mtevent", "mtev"])
    raw_heat = _lookup(["heat", "fin_heat", "pre_heat", "heat_no"])
    raw_lane = _lookup(["lane", "fin_lane", "pre_lane", "lane_no"])
    raw_time = _lookup(["time", "fin_time", "pad_time", "final_time", "result_time"])
    raw_place = _lookup(["place", "fin_place", "rank"])
    raw_status = _lookup(["status", "fin_stat", "stat", "dq"])

    try:
        event_no = int(str(raw_event).strip())
        heat = int(str(raw_heat).strip())
        lane = int(str(raw_lane).strip())
    except (TypeError, ValueError):
        return None

    if event_no <= 0 or heat <= 0 or lane <= 0:
        return None

    time_sec, inferred_status = parse_time_value(raw_time)
    status_str = str(raw_status).strip().upper() if raw_status is not None else ""
    if not status_str and inferred_status:
        status_str = inferred_status
    if status_str == "Q":
        status_str = "DQ"
    elif status_str == "R":
        status_str = "SCR"

    place = 0
    if raw_place is not None and str(raw_place).strip():
        try:
            place = int(float(str(raw_place).strip()))
        except ValueError:
            place = 0

    return {
        "event": event_no,
        "heat": heat,
        "lane": lane,
        "time": time_sec,
        "place": place,
        "status": status_str,
    }


def parse_timing_result_chunk(filename: str, raw_bytes: bytes) -> list[dict[str, Any]]:
    """Parse incremental timing system output (JSON, CSV, or CTS/Dolphin semicolon format)."""
    if not raw_bytes:
        return []

    text = raw_bytes.decode("utf-8", errors="replace").strip()
    if not text:
        return []

    # 1. Try JSON first if filename ends with .json or text starts with '[' / '{'
    if filename.lower().endswith(".json") or text.startswith("[") or text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                raw_list = parsed.get("results", [parsed])
            elif isinstance(parsed, list):
                raw_list = parsed
            else:
                raw_list = []

            normalized: list[dict[str, Any]] = []
            for entry in raw_list:
                if isinstance(entry, dict):
                    norm = _normalize_result_item(entry)
                    if norm:
                        normalized.append(norm)
            return normalized
        except json.JSONDecodeError as err:
            if filename.lower().endswith(".json"):
                raise ValueError(f"Invalid JSON in timing result chunk: {filename}") from err

    # 2. Delimited text (CSV, Colorado Time Systems / Dolphin semicolon, or whitespace/pipe)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        return []

    delimiter = ";" if ";" in lines[0] else ","
    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    if not rows:
        return []

    first_row_lower = [c.strip().lower() for c in rows[0]]
    has_header = any(tok in first_row_lower for tok in ("event", "event_no", "heat", "lane", "time", "fin_time"))

    results: list[dict[str, Any]] = []
    if has_header:
        headers = first_row_lower
        for row in rows[1:]:
            row_dict = {headers[i]: row[i].strip() for i in range(min(len(headers), len(row)))}
            norm = _normalize_result_item(row_dict)
            if norm:
                results.append(norm)
    else:
        for row in rows:
            cleaned = [c.strip() for c in row]
            if len(cleaned) < 4:
                continue
            item: dict[str, Any] = {
                "event": cleaned[0],
                "heat": cleaned[1],
                "lane": cleaned[2],
                "time": cleaned[3],
            }
            if len(cleaned) >= 5:
                item["place"] = cleaned[4]
            if len(cleaned) >= 6:
                item["status"] = cleaned[5]
            norm = _normalize_result_item(item)
            if norm:
                results.append(norm)

    return results


def _set_case_preserving_field(row: dict[str, Any], candidates: list[str], value: Any) -> None:
    """Set a field on a dataset row dictionary, preserving existing casing when present."""
    for cand in candidates:
        if cand in row:
            row[cand] = value
            return
        lower_cand = cand.lower()
        for existing_key in list(row.keys()):
            if existing_key.lower().strip() == lower_cand:
                row[existing_key] = value
                return
    row[candidates[0]] = value


def apply_live_results_to_cache(
    cache: dict[str, Any],
    results: list[dict[str, Any]],
    servicer: Any,
) -> int:
    """Apply normalized live timing results to the in-memory dataset cache."""
    if not cache or not results:
        return 0

    events = servicer._get_table(cache, "event")
    entries = servicer._get_table(cache, "entry")
    relays = servicer._get_table(cache, "relay")

    event_no_to_ptrs: dict[int, set[int]] = {}
    for ev in events:
        ev_no = servicer._safe_int(
            servicer._get_field(ev, ["event_no", "Event_no", "mtev", "MtEv", "mtevent", "MtEvent"])
        )
        ev_ptr = servicer._safe_int(
            servicer._get_field(ev, ["event_ptr", "Event_ptr", "mtevent", "MtEvent", "event_no", "Event_no"])
        )
        if ev_no > 0:
            ptrs = event_no_to_ptrs.setdefault(ev_no, {ev_no})
            if ev_ptr > 0:
                ptrs.add(ev_ptr)

    updated_count = 0

    for res in results:
        ev_no = int(res.get("event", 0))
        heat = int(res.get("heat", 0))
        lane = int(res.get("lane", 0))
        time_sec = res.get("time")
        place = int(res.get("place", 0) or 0)
        status = str(res.get("status", "") or "")

        candidate_ptrs = event_no_to_ptrs.get(ev_no, {ev_no})

        for table in (entries, relays):
            for row in table:
                row_ev = servicer._safe_int(
                    servicer._get_field(row, ["event_ptr", "Event_ptr", "mtevent", "MtEvent", "event_no", "Event_no"])
                )
                if row_ev not in candidate_ptrs:
                    continue

                fin_heat = servicer._safe_int(servicer._get_field(row, ["fin_heat", "Fin_heat", "heat", "HEAT"]))
                pre_heat = servicer._safe_int(servicer._get_field(row, ["pre_heat", "Pre_heat"]))
                fin_lane = servicer._safe_int(servicer._get_field(row, ["fin_lane", "Fin_lane", "lane", "LANE"]))
                pre_lane = servicer._safe_int(servicer._get_field(row, ["pre_lane", "Pre_lane"]))

                heat_matches = (fin_heat == heat and fin_lane == lane) or (pre_heat == heat and pre_lane == lane)
                if not heat_matches:
                    continue

                if time_sec is not None:
                    _set_case_preserving_field(row, ["fin_time", "Fin_time", "score", "Score"], time_sec)
                if place > 0:
                    _set_case_preserving_field(row, ["fin_place", "Fin_place", "place"], place)
                if status:
                    mm_stat = "Q" if status == "DQ" else ("R" if status == "SCR" else status)
                    _set_case_preserving_field(row, ["fin_stat", "Fin_stat"], mm_stat)
                    if status == "DQ":
                        _set_case_preserving_field(row, ["fin_time", "Fin_time"], 0.0)

                updated_count += 1

    return updated_count


def apply_stored_live_results(uid: str, cache: dict[str, Any], servicer: Any) -> int:
    """Load persisted live timing results for ``uid`` (if any) and overlay them onto ``cache``."""
    if not cache or not uid:
        return 0

    live_path = os.path.join("users", uid, LIVE_RESULTS_REL_PATH)
    if not servicer.storage.exists(live_path):
        return 0

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        servicer.storage.download_file(live_path, tmp_path)
        with open(tmp_path, encoding="utf-8") as f:
            stored = json.load(f)
        if isinstance(stored, list) and stored:
            return apply_live_results_to_cache(cache, stored, servicer)
        return 0
    except Exception as exc:
        logging.warning("Failed to apply stored live results for %s: %s", servicer._mask_uid(uid), exc)
        return 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def upload_result_chunk(
    request: Any,
    context: grpc.ServicerContext,
    servicer: LiveResultServicerContext,
    pb2: Any,
) -> Any:
    """Ingest an incremental timing system result chunk and update the active dataset."""
    from handlers.auth_utils import get_data_access_token

    token = get_data_access_token()
    if token and getattr(request, "access_token", "") == token and getattr(request, "uid", ""):
        uid = request.uid
        logging.info("UploadResultChunk: Authenticated via system token for user %s", servicer._mask_uid(uid))
    else:
        uid = servicer._check_auth(context)

    filename = getattr(request, "filename", "") or "chunk.csv"
    raw_bytes = getattr(request, "content", b"") or b""

    try:
        parsed_results = parse_timing_result_chunk(filename, raw_bytes)
        if not parsed_results:
            return pb2.UploadResultChunkResponse(
                success=False,
                message=f"No valid timing result records found in {filename}",
                updated_count=0,
            )

        # Merge with existing persisted live results for this user
        live_path = os.path.join("users", uid, LIVE_RESULTS_REL_PATH)
        merged_by_key: dict[tuple[int, int, int], dict[str, Any]] = {}

        if servicer.storage.exists(live_path):
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp_in:
                tmp_in_path = tmp_in.name
            try:
                servicer.storage.download_file(live_path, tmp_in_path)
                with open(tmp_in_path, encoding="utf-8") as f:
                    existing = json.load(f)
                if isinstance(existing, list):
                    for item in existing:
                        if isinstance(item, dict):
                            k = (int(item.get("event", 0)), int(item.get("heat", 0)), int(item.get("lane", 0)))
                            merged_by_key[k] = item
            except Exception as exc:
                logging.warning("UploadResultChunk: Could not read previous live results: %s", exc)
            finally:
                if os.path.exists(tmp_in_path):
                    os.remove(tmp_in_path)

        for item in parsed_results:
            k = (int(item["event"]), int(item["heat"]), int(item["lane"]))
            merged_by_key[k] = item

        merged_list = list(merged_by_key.values())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp_out:
            json.dump(merged_list, tmp_out, indent=2)
            tmp_out_path = tmp_out.name

        try:
            servicer.storage.upload_file(tmp_out_path, live_path)
        finally:
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)

        # Load dataset (or use cached dataset) and apply the newly uploaded chunk
        cache, _ = servicer._load_user_data(context)
        updated_count = apply_live_results_to_cache(cache, parsed_results, servicer)

        if uid in servicer._user_cache:
            servicer._user_cache[uid]["data"] = cache

        return pb2.UploadResultChunkResponse(
            success=True,
            message=f"Processed {len(parsed_results)} result record(s) from {filename}; updated {updated_count} entry/relay row(s)",
            updated_count=updated_count,
        )
    except Exception as exc:
        logging.error("UploadResultChunk failed: %s", exc)
        return pb2.UploadResultChunkResponse(
            success=False,
            message=str(exc),
            updated_count=0,
        )
