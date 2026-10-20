"""Handler for processing dataset uploads (MDB/ZIP/JSON)."""

from __future__ import annotations

import io
import logging
import os
import tempfile
import zipfile
from collections import OrderedDict
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import threading

    import grpc

    from meetmanager.v1 import meet_manager_pb2 as pb2
    from storage_provider import StorageProvider


class ServicerContextLike(Protocol):
    """Protocol specifying the required methods and attributes of the parent Servicer."""

    storage: StorageProvider
    _lock: threading.RLock
    _user_cache: OrderedDict[str, dict[str, Any]]

    def _check_auth(self, context: grpc.ServicerContext) -> str: ...

    def _mask_uid(self, uid: str) -> str: ...

    def _mask_path(self, path: str) -> str: ...

    def _load_user_config(self, context: grpc.ServicerContext) -> dict[str, Any]: ...

    def _save_user_config(self, context: grpc.ServicerContext, config: dict[str, Any]) -> None: ...


def upload_dataset(
    request_iterator: Iterator[pb2.UploadDatasetRequest],
    context: grpc.ServicerContext,
    service: ServicerContextLike,
    pb2_module: Any,
) -> pb2.UploadDatasetResponse:
    """Processes the upload and extraction of a dataset.

    Args:
        request_iterator: Iterator of request chunks containing the file.
        context: The gRPC context containing metadata for authentication.
        service: The servicer instance conforming to ServicerContextLike.
        pb2_module: The generated protobuf module containing response classes.

    Returns:
        The protobuf UploadDatasetResponse indicating success or failure.
    """
    logging.debug("DEBUG: UploadDataset called (delegated)")
    uid = service._check_auth(context)
    filename = None

    # Temporary buffer to hold file content
    file_content = io.BytesIO()
    total_bytes = 0

    try:
        for request in request_iterator:
            if request.HasField("filename") and request.filename:
                filename = os.path.basename(request.filename)
                ext = os.path.splitext(filename)[1].lower()
                if ext not in [".mdb", ".json", ".zip"]:
                    # Default to .mdb for backward compatibility if invalid extension
                    if not filename.lower().endswith(".mdb"):
                        filename += ".mdb"

            if request.HasField("chunk"):
                chunk_len = len(request.chunk)
                file_content.write(request.chunk)
                total_bytes += chunk_len

        if not filename:
            filename = "uploaded.mdb"

        logging.info(f"UploadDataset: Final filename for {service._mask_uid(uid)} is {filename}")
        user_path = os.path.join("users", uid, filename)
        logging.info(f"UploadDataset: Targeting user_path={service._mask_path(user_path)} for {service._mask_uid(uid)}")

        if hasattr(service.storage, "base_dir"):
            logging.info(
                f"UploadDataset: saving to {service._mask_path(user_path)} (abs masked) for {service._mask_uid(uid)}"
            )
        else:
            logging.info(f"UploadDataset: saving to {service._mask_path(user_path)} for {service._mask_uid(uid)}")

        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            file_content.seek(0)
            tmp.write(file_content.getvalue())
            tmp_path = tmp.name
            tmp.flush()
            tmp.close()

        # Handle ZIP files
        if suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(tmp_path, "r") as z:
                    mdb_files = [f for f in z.namelist() if f.lower().endswith(".mdb") and not z.getinfo(f).is_dir()]
                    if not mdb_files:
                        raise Exception("No .mdb file found inside the uploaded ZIP archive")

                    mdb_member = mdb_files[0]
                    filename = os.path.basename(mdb_member)
                    user_path = os.path.join("users", uid, filename)
                    logging.info(f"UploadDataset: Extracted '{filename}' from uploaded ZIP archive")

                    with tempfile.NamedTemporaryFile(suffix=".mdb", delete=False) as tmp_mdb:
                        tmp_mdb.write(z.read(mdb_member))
                        new_tmp_path = tmp_mdb.name
                        tmp_mdb.flush()
                        tmp_mdb.close()

                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                tmp_path = new_tmp_path
            except Exception as zip_err:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise Exception(f"Failed to extract ZIP: {str(zip_err)}") from zip_err

        preloaded_cache: dict[str, Any] | None = None
        try:
            service.storage.upload_file(tmp_path, user_path)
            if hasattr(os, "sync"):
                os.sync()
            # Pre-parse dataset directly from local tmp_path (if non-empty) so post-upload SSR queries
            # do not need to re-download the file from GCS.
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                try:
                    if filename.lower().endswith(".mdb") and hasattr(service, "_load_mdb"):
                        loaded = service._load_mdb(tmp_path)
                        if loaded:
                            preloaded_cache = loaded
                    elif filename.lower().endswith(".json"):
                        import json

                        from mm_to_json.mm_to_json import MmToJsonConverter

                        with open(tmp_path) as f_json:
                            raw_data = json.load(f_json)
                        converter = MmToJsonConverter(table_data=raw_data)
                        preloaded_cache = converter.export_raw()
                except Exception as preload_err:
                    logging.debug(f"UploadDataset: Preload skipped for {filename}: {preload_err}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        logging.info(f"Saved uploaded file to {service._mask_path(user_path)}")

        with service._lock:
            # Update active dataset in config
            config = service._load_user_config(context)
            config["active_dataset"] = filename
            service._save_user_config(context, config)

            # Invalidate or populate cache for the new dataset
            if uid in service._user_cache:
                del service._user_cache[uid]
                logging.info(f"Invalidated cache for user {service._mask_uid(uid)} due to UploadDataset")

            if preloaded_cache:
                try:
                    from handlers.live_result_handler import apply_stored_live_results

                    apply_stored_live_results(uid, preloaded_cache, service)
                except Exception:
                    pass
                mtime = service.storage.get_last_modified(user_path) if hasattr(service.storage, "base_dir") else 0.0
                service._user_cache[uid] = {
                    "filename": filename,
                    "mtime": mtime,
                    "data": preloaded_cache,
                    "config": dict(config),
                }
                service._user_cache.move_to_end(uid)
                logging.info(f"Pre-populated cache for user {service._mask_uid(uid)}/{filename}")

        return pb2_module.UploadDatasetResponse(success=True, message=f"Saved {filename}")

    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return pb2_module.UploadDatasetResponse(success=False, message=str(e))
