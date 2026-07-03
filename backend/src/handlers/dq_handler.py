from __future__ import annotations

import json
import logging
import os
import tempfile
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Protocol

import grpc

if TYPE_CHECKING:
    from storage_provider import StorageProvider


class DQServicerContext(Protocol):
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


def sync_dqs(request: Any, context: grpc.ServicerContext, servicer: DQServicerContext, pb2: Any) -> Any:
    """Synchronizes DQ logs and write-backs into the active Microsoft Access .mdb file."""
    from handlers.auth_utils import get_data_access_token

    token = get_data_access_token()
    uid = request.uid

    logging.info(
        f"SyncDQs: Received request for UID: {servicer._mask_uid(uid)}, Payload length: {len(request.dqs_json)}"
    )

    if token and request.access_token == token:
        uid = request.uid
        logging.info(f"SyncDQs: Authenticated via system token for user {servicer._mask_uid(uid)}")
    else:
        uid = servicer._check_auth(context)

    dqs_json = request.dqs_json

    try:
        # Parse to validate
        dqs = json.loads(dqs_json)

        # Save to user's dataset directory (as backup/log)
        filename = "synced_dqs.json"
        user_path = os.path.join("users", uid, filename)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(dqs, tmp, indent=2)
            tmp_path = tmp.name

        try:
            servicer.storage.upload_file(tmp_path, user_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # Update the master database if it's an MDB
        config = servicer._load_user_config(context)
        active_filename = config.get("active_dataset")
        if active_filename and active_filename.lower().endswith(".mdb"):
            dataset_path = os.path.join("users", uid, active_filename)
            if servicer.storage.exists(dataset_path):
                logging.info(
                    f"Syncing DQs to MDB: {servicer._mask_path(dataset_path)} for user {servicer._mask_uid(uid)}"
                )

                # Download MDB to local temp for writing
                with tempfile.NamedTemporaryFile(suffix=".mdb", delete=False) as tmp_mdb:
                    tmp_mdb_path = tmp_mdb.name
                    tmp_mdb.close()

                try:
                    servicer.storage.download_file(dataset_path, tmp_mdb_path)

                    # Resolve event pointers and relay status from human-readable numbers
                    cache, _ = servicer._load_user_data(context)
                    event_table = servicer._get_table(cache, "event")
                    # Map eventNum (human #) to {ptr, is_relay}
                    event_info_map = {}
                    for e in event_table:
                        h_num = servicer._safe_int(
                            servicer._get_field(e, ["event_no", "Event_no"])
                            or servicer._get_field(e, ["mtevent", "Mtevent"])
                        )
                        e_ptr = servicer._get_field(e, ["event_ptr", "Event_ptr"]) or servicer._get_field(
                            e, ["mtevent", "Mtevent"]
                        )
                        is_relay = (
                            str(servicer._get_field(e, ["Ind_rel", "ind_rel", "i_r", "I_r"]) or "").upper() == "R"
                        )

                        if h_num and e_ptr:
                            event_info_map[h_num] = {"ptr": e_ptr, "is_relay": is_relay}

                    from mm_to_json import mdb_writer

                    db = mdb_writer.open_db(tmp_mdb_path)
                    try:
                        updated_count = 0
                        for dq in dqs:
                            event_id = dq.get("event_id")
                            athlete_id = dq.get("swimmer_id")
                            dq_code = dq.get("dq_code", "")
                            notes = dq.get("notes", "")
                            heat = servicer._safe_int(dq.get("heat", 0))
                            lane = servicer._safe_int(dq.get("lane", 0))

                            info = event_info_map.get(servicer._safe_int(event_id))
                            if info and athlete_id:
                                if mdb_writer.update_entry_status(
                                    db,
                                    info["ptr"],
                                    athlete_id,
                                    heat,
                                    lane,
                                    status="DQ",
                                    dq_code=dq_code,
                                    is_relay=info["is_relay"],
                                ):
                                    updated_count += 1
                                    logging.info(
                                        f"Updated MDB DQ for swimmer {athlete_id} in event {event_id}. Notes: {notes}"
                                    )

                        db.close()
                        # Upload updated MDB back to storage
                        servicer.storage.upload_file(tmp_mdb_path, dataset_path)

                        # Force cache invalidation so Next.js/Web-Client sees the DQ
                        if uid in servicer._user_cache:
                            del servicer._user_cache[uid]
                        logging.info(
                            f"Successfully updated {updated_count} entries in MDB for {servicer._mask_uid(uid)}"
                        )
                    finally:
                        try:
                            db.close()
                        except Exception:
                            pass
                finally:
                    if os.path.exists(tmp_mdb_path):
                        os.remove(tmp_mdb_path)

        logging.info(f"Synced {len(dqs)} DQs for user {servicer._mask_uid(uid)}")
        return pb2.SyncDQsResponse(success=True, message=f"Synced {len(dqs)} items")
    except Exception as e:
        logging.error(f"Sync failed: {e}")
        return pb2.SyncDQsResponse(success=False, message=str(e))
