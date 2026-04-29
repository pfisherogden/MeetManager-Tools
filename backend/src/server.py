from __future__ import annotations

import datetime
import io
import json
import logging
import multiprocessing
import os
import tempfile
import threading
import time
import uuid
import zipfile
from collections import OrderedDict
from concurrent import futures
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import grpc
import msgpack

# Import generated classes
try:
    from meetmanager.v1 import meet_manager_pb2 as pb2
    from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc
except ImportError:
    # Fallback for environments where protos aren't generated yet
    # We use cast to Any to avoid mypy errors when this fallback is active
    import typing

    pb2 = typing.cast(Any, None)
    pb2_grpc = typing.cast(Any, None)

from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from auth_interceptor import FirebaseAuthInterceptor
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.playwright_renderer import PlaywrightRenderer
from mm_to_json.reporting.weasy_renderer import WeasyRenderer
from storage_provider import GCSStorageProvider, LocalStorageProvider, StorageProvider

# Configure logging
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", force=True)

# Suppress verbose third-party loggers unless explicitly requested
if log_level_str != "DEBUG":
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    logging.getLogger("weasyprint").setLevel(logging.WARNING)
    logging.getLogger("jpype").setLevel(logging.WARNING)

# Defines where the source JSON data lives
DATA_DIR = "../data"
SOURCE_FILE = "Sample_Data.json"
CONFIG_FILE = "config.json"
MAX_CACHE_SIZE = 3  # Keep only the last 3 users' data in memory


class JobManager:
    """Manages the state of background jobs using Firestore if available, otherwise in-memory."""

    def __init__(self):
        self.use_firestore = False
        self.in_memory_jobs: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

        # Check if we should use Firestore (if in production or emulator is explicitly set)
        if os.getenv("K_SERVICE") or os.getenv("FIRESTORE_EMULATOR_HOST") or os.getenv("USE_FIRESTORE") == "true":
            try:
                import firebase_admin
                from firebase_admin import firestore

                try:
                    self.app = firebase_admin.get_app()
                except ValueError:
                    self.app = firebase_admin.initialize_app()

                self.db = firestore.client()
                self.collection = self.db.collection("jobs")
                self.use_firestore = True
                logging.info("JobManager: Using Firestore for persistent job tracking")
            except Exception as e:
                logging.warning(
                    f"JobManager: Firestore initialization failed ({e}). Falling back to in-memory tracking."
                )

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())

        initial_state = {
            "status": pb2.JOB_STATUS_PENDING,
            "progress": 0.0,
            "message": "Job queued",
            "bundle_url": "",
        }

        if self.use_firestore:
            from firebase_admin import firestore

            doc_ref = self.collection.document(job_id)
            doc_ref.set(
                {
                    **initial_state,
                    "created_at": firestore.SERVER_TIMESTAMP,
                }
            )
        else:
            with self.lock:
                self.in_memory_jobs[job_id] = initial_state

        return job_id

    def update_job(
        self,
        job_id: str,
        status: int | None = None,
        progress: float | None = None,
        message: str | None = None,
        bundle_url: str | None = None,
    ) -> None:
        if self.use_firestore:
            from firebase_admin import firestore

            doc_ref = self.collection.document(job_id)
            updates: dict[str, Any] = {"updated_at": firestore.SERVER_TIMESTAMP}
            if status is not None:
                updates["status"] = status
            if progress is not None:
                updates["progress"] = progress
            if message is not None:
                updates["message"] = message
            if bundle_url is not None:
                updates["bundle_url"] = bundle_url
            doc_ref.update(updates)
        else:
            with self.lock:
                if job_id in self.in_memory_jobs:
                    # Perform atomic dict update
                    updates = {}
                    if status is not None:
                        updates["status"] = status
                    if progress is not None:
                        updates["progress"] = progress
                    if message is not None:
                        updates["message"] = message
                    if bundle_url is not None:
                        updates["bundle_url"] = bundle_url
                    self.in_memory_jobs[job_id].update(updates)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        if self.use_firestore:
            doc_ref = self.collection.document(job_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        else:
            with self.lock:
                return self.in_memory_jobs.get(job_id)


def msgpack_encode(obj):
    """Custom encoder for msgpack to handle datetimes and other types."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def _process_single_report_process(
    report_req_type,
    report_req_title,
    report_req_team_filter,
    report_req_gender_filter,
    report_req_age_group_filter,
    user_id,
    columns_on_page,
    show_relay_swimmers,
    zebra_striping,
    msgpack_path,
    rtype_map,
    renderer_type=None,
    html_preview=False,
    idx=0,
):
    import datetime
    import logging
    import os
    import tempfile
    import traceback

    import msgpack

    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", force=True)
    if log_level_str != "DEBUG":
        logging.getLogger("fontTools").setLevel(logging.WARNING)
        logging.getLogger("weasyprint").setLevel(logging.WARNING)
    from mm_to_json.reporting.extractor import ReportDataExtractor

    rtype = rtype_map.get(report_req_type, "psych")
    title = report_req_title
    start_time = datetime.datetime.now()
    try:
        with open(msgpack_path, "rb") as f:
            unpacked = msgpack.unpack(f, raw=False)
            full_data = unpacked["full_data"]
            cache_data = unpacked["cache"]
        load_duration = (datetime.datetime.now() - start_time).total_seconds()
        render_start_time = datetime.datetime.now()
        is_html = html_preview or (rtype == "program_html")
        temp_fd, temp_path = tempfile.mkstemp(suffix=".html" if is_html else ".pdf")
        os.close(temp_fd)

        from mm_to_json.mm_to_json import MmToJsonConverter

        converter = MmToJsonConverter(table_data=cache_data)
        extractor = ReportDataExtractor(converter, full_data=full_data)
        renderer: Any
        if renderer_type == "playwright":
            renderer = PlaywrightRenderer(output_path=temp_path)
        else:
            renderer = WeasyRenderer(output_path=temp_path)

        report_data = None
        if rtype == "psych":
            report_data = extractor.extract_psych_sheet_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "psych_sheet.j2"
        elif rtype == "entries":
            report_data = extractor.extract_meet_entries_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "meet_entries.j2"
        elif rtype == "lineups":
            # Fallback to entries for lineups if not explicitly implemented
            report_data = extractor.extract_meet_entries_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "lineups.j2"
        elif rtype == "results":
            report_data = extractor.extract_results_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "results.j2"
        elif rtype == "entries_club":
            report_data = extractor.extract_meet_entries_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "entries_club.j2"
        elif rtype == "lane_timer_sheets":
            report_data = extractor.extract_lane_timer_sheets_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
            )
            template = "timer_sheets.j2"
        elif rtype in ["program", "program_html", "judge_sheets"]:
            report_data = extractor.extract_meet_program_data(
                team_filter=report_req_team_filter,
                report_title=title,
                gender_filter=report_req_gender_filter,
                age_group_filter=report_req_age_group_filter,
                columns_on_page=columns_on_page,
                show_relay_swimmers=show_relay_swimmers,
                show_dq_lines=(rtype == "judge_sheets"),
            )
            template = "meet_program.j2"
        if report_data:
            report_data["zebra_striping"] = zebra_striping
            if is_html:
                html_content = renderer.render_to_html(report_data, template_name=template)
                with open(temp_path, "wb") as f:
                    f.write(html_content.encode("utf-8"))
            else:
                if template == "meet_program.j2":
                    renderer.render_meet_program(report_data)
                else:
                    renderer.render_entries(report_data, template)
        if os.path.exists(temp_path):
            with open(temp_path, "rb") as f:
                pdf_bytes = f.read()
            os.unlink(temp_path)
        else:
            pdf_bytes = b""
        render_duration = (datetime.datetime.now() - render_start_time).total_seconds()
        ext = ".html" if is_html else ".pdf"
        final_filename = f"{user_id}_{title}{ext}"
        html_str = pdf_bytes.decode("utf-8") if is_html else ""
        return {
            "success": True,
            "content": pdf_bytes,
            "filename": final_filename,
            "html_content": html_str,
            "rtype": rtype,
            "idx": idx,
            "load_duration": load_duration,
            "render_duration": render_duration,
        }
    except Exception as e:
        logging.error(f"Error in _process_single_report_process (idx {idx}): {traceback.format_exc()}")
        return {"success": False, "error": str(e), "rtype": rtype, "idx": idx}


class MeetManagerService(pb2_grpc.MeetManagerServiceServicer):
    def __init__(self):
        # Initialize storage provider
        self.storage: StorageProvider
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if bucket_name:
            self.storage = GCSStorageProvider(bucket_name)
        else:
            base_storage_dir = os.path.join(os.path.dirname(__file__), DATA_DIR)
            self.storage = LocalStorageProvider(base_storage_dir)

        self._user_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.current_file = SOURCE_FILE
        self.job_manager = JobManager()
        self._lock = threading.RLock()
        # Note: We don't load data in __init__ anymore because it's per-user
        # self._load_data()
        # self._load_config()

    def _get_user_path(self, context, filename=""):
        uid = self._check_auth(context)
        return os.path.join("users", uid, filename)

    def _check_auth(self, context):
        """Helper to ensure the request is authenticated with robust UID detection."""
        if context is not None:
            try:
                # 1. Direct Metadata Search (Case-insensitive)
                metadata = {k.lower(): v for k, v in context.invocation_metadata()}
                uid = metadata.get("x-e2e-uid") or metadata.get("x-user-id")

                # 2. Cookie Search (Backup for browser-based calls in Safari)
                if not uid:
                    cookie_header = metadata.get("cookie") or metadata.get("Cookie") or ""
                    # Handle if cookie is a list (rare but possible in some gRPC wrappers)
                    cookie_str = cookie_header[0] if isinstance(cookie_header, list) else cookie_header
                    if cookie_str:
                        for part in cookie_str.split(";"):
                            pair = part.strip().split("=", 1)
                            if len(pair) == 2:
                                name, value = pair
                                if name.lower() in ["x-user-id", "x-e2e-uid"]:
                                    uid = value
                                    break

                if uid:
                    return uid

                # 3. Log metadata keys if UID is missing in E2E mode
                if os.getenv("IS_E2E") == "true":
                    logging.debug(f"DEBUG: No UID found in metadata. Available keys: {list(metadata.keys())}")

            except (AttributeError, TypeError) as e:
                logging.debug(f"DEBUG: Auth metadata extraction failed: {e}")

        uid = getattr(context, "uid", None)
        if uid is not None:
            return uid

        # Fallback for local development or testing
        if os.getenv("GRPC_AUTH_DISABLED") == "true" or not os.getenv("K_SERVICE"):
            return "dev-user"

        context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication required")
        return "unauthenticated"  # Should not reach here due to abort

    def _load_user_config(self, context):
        with self._lock:
            uid = self._check_auth(context)
            config_path = os.path.join("users", uid, CONFIG_FILE)
            if self.storage.exists(config_path):
                tmp_path = ""
                with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                    tmp_path = tmp.name
                    tmp.close()

                try:
                    self.storage.download_file(config_path, tmp_path)
                    with open(tmp_path) as f:
                        config = json.load(f)
                        return config
                except Exception as e:
                    logging.debug(f"DEBUG: Failed to load user config for {uid}: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

            return {"meet_name": "", "meet_description": "", "active_dataset": SOURCE_FILE}

    def _save_user_config(self, context, config):
        with self._lock:
            uid = self._check_auth(context)
            config_path = os.path.join("users", uid, CONFIG_FILE)
            tmp_path = ""
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                json.dump(config, tmp, indent=2)
                tmp_path = tmp.name
                tmp.flush()
                # Close it explicitly before uploading
                tmp.close()

            try:
                self.storage.upload_file(tmp_path, config_path)
                if hasattr(os, "sync"):
                    os.sync()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    def _load_user_data(self, context):
        with self._lock:
            config = self._load_user_config(context)
            filename = config.get("active_dataset", SOURCE_FILE)
            uid = self._check_auth(context)

            # E2E Check: Completely ignore the cache if x-e2e-uid/x-user-id is present or IS_E2E is set
            metadata = {k.lower(): v for k, v in (context.invocation_metadata() if context else [])}
            is_e2e = os.getenv("IS_E2E") == "true" or "x-e2e-uid" in metadata or "x-user-id" in metadata
            if not is_e2e and "cookie" in metadata:
                is_e2e = "x-user-id=" in str(metadata["cookie"]).lower()

            user_path = os.path.join("users", uid, filename)
            storage_exists = self.storage.exists(user_path)

            if is_e2e:
                logging.info(f"E2E: uid={uid}, file={user_path}, exists={storage_exists}")

            # Check cache (Skip if E2E)
            if not is_e2e and uid in self._user_cache:
                entry = self._user_cache[uid]
                # Move to end (most recent)
                self._user_cache.move_to_end(uid)

                if entry["filename"] == filename:
                    # Check if modified
                    try:
                        mtime = self.storage.get_last_modified(user_path)
                        if mtime == entry["mtime"]:
                            logging.debug(f"DEBUG: Returning cached data for {uid}/{filename}")
                            return entry["data"], config
                        else:
                            logging.debug(
                                f"DEBUG: Cache stale for {uid}/{filename} (mtime {mtime} != {entry['mtime']})"
                            )
                    except Exception as e:
                        logging.debug(f"DEBUG: Cache check error for {uid}/{filename}: {e}")
                        pass  # Force reload on error

            if not storage_exists:
                logging.debug(f"DEBUG: User file {user_path} NOT FOUND in storage.")
                # Fallback for prototype: check global Sample_Data.json
                if self.storage.exists(SOURCE_FILE):
                    logging.debug(f"DEBUG: Falling back to global {SOURCE_FILE}")
                    user_path = SOURCE_FILE
                    filename = SOURCE_FILE
                else:
                    logging.debug(f"DEBUG: Global fallback {SOURCE_FILE} also NOT FOUND.")
                    return {}, config
            else:
                logging.debug(f"DEBUG: Found user file at {user_path}")

            logging.debug(f"DEBUG: Loading data from {user_path}...")
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
                tmp_path = tmp.name
                tmp.close()  # Close to avoid locking

            try:
                self.storage.download_file(user_path, tmp_path)
                if filename.endswith(".mdb"):
                    cache = self._load_mdb(tmp_path)
                else:
                    with open(tmp_path) as f:
                        raw_data = json.load(f)

                    # Use converter to normalize keys/types even for JSON
                    # This ensures table names (Meet -> meet) and column names are normalized
                    converter = MmToJsonConverter(table_data=raw_data)
                    cache = converter.export_raw()

                # Update cache
                try:
                    mtime = self.storage.get_last_modified(user_path)
                    self._user_cache[uid] = {"filename": filename, "mtime": mtime, "data": cache}
                    self._user_cache.move_to_end(uid)

                    # Evict oldest if limit exceeded
                    if len(self._user_cache) > MAX_CACHE_SIZE:
                        oldest_uid, _ = self._user_cache.popitem(last=False)
                        logging.debug(f"DEBUG: Evicted {oldest_uid} from user cache to save memory")

                    logging.debug(f"DEBUG: Data loaded and cached for {uid}/{filename} (mtime: {mtime})")
                except Exception as e:
                    logging.debug(f"DEBUG: Failed to update cache for {uid}/{filename}: {e}")

                return cache, config
            except Exception as e:
                logging.error(f"DEBUG: Error loading data from {user_path}: {e}")
                return {}, config
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    def _load_mdb(self, path):
        """Parsing MDB using MmToJsonConverter (Jackcess/JPype) for performance."""
        # Copy to temp file to avoid locking issues
        with tempfile.NamedTemporaryFile(suffix=".mdb", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with open(path, "rb") as src, open(tmp_path, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)

            converter = MmToJsonConverter(mdb_path=tmp_path)
            # Use export_raw for consistent normalization with JSON loading
            return converter.export_raw()
        except Exception as e:
            logging.error(f"Error loading MDB: {e}")
            return {}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def UploadDataset(self, request_iterator, context):
        logging.debug("DEBUG: UploadDataset called")
        uid = self._check_auth(context)
        filename = "uploaded.mdb"

        # Temporary buffer to hold file content
        file_content = io.BytesIO()
        total_bytes = 0

        try:
            for request in request_iterator:
                if request.HasField("filename"):
                    filename = os.path.basename(request.filename)
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in [".mdb", ".json"]:
                        # If no valid extension, default to .mdb for backward compatibility
                        if not filename.lower().endswith(".mdb"):
                            filename += ".mdb"

                if request.HasField("chunk"):
                    chunk_len = len(request.chunk)
                    file_content.write(request.chunk)
                    total_bytes += chunk_len

            logging.info(f"UploadDataset: uid={uid}, received total {total_bytes} bytes for {filename}")

            # Upload to storage provider
            user_path = os.path.join("users", uid, filename)
            # For LocalStorageProvider, print absolute path for debugging
            if hasattr(self.storage, "base_dir"):
                abs_user_path = os.path.abspath(os.path.join(self.storage.base_dir, user_path))
                logging.info(f"UploadDataset: saving to {user_path} (abs: {abs_user_path}) for {uid}")
            else:
                logging.info(f"UploadDataset: saving to {user_path} for {uid}")

            suffix = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                file_content.seek(0)
                tmp.write(file_content.getvalue())
                tmp_path = tmp.name
                tmp.flush()
                tmp.close()

            try:
                self.storage.upload_file(tmp_path, user_path)
                # FORCE FS SYNC for E2E consistency
                if hasattr(os, "sync"):
                    os.sync()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            logging.info(f"Saved uploaded file to {user_path}")

            with self._lock:
                # Update active dataset in config
                config = self._load_user_config(context)
                config["active_dataset"] = filename
                self._save_user_config(context, config)

                # Invalidate cache to force reload of the new dataset
                if uid in self._user_cache:
                    del self._user_cache[uid]

            return pb2.UploadDatasetResponse(success=True, message=f"Saved {filename}")
        except Exception as e:
            logging.error(f"Upload failed: {e}")
            return pb2.UploadDatasetResponse(success=False, message=str(e))

    def GetDashboardStats(self, request, context):
        request = request or pb2.GetDashboardStatsRequest()
        cache, _ = self._load_user_data(context)

        teams = cache.get("team", [])
        athletes = cache.get("athlete", [])
        events = cache.get("event", [])
        meets = cache.get("meet", [])

        return pb2.GetDashboardStatsResponse(
            meet_count=len(meets), team_count=len(teams), athlete_count=len(athletes), event_count=len(events)
        )

    def _get_team_color(self, team_id: int) -> str:
        """Assign a stable, pleasing color to a team based on its ID."""
        palette = [
            "#3b82f6",  # blue-500
            "#ef4444",  # red-500
            "#10b981",  # emerald-500
            "#f59e0b",  # amber-500
            "#8b5cf6",  # violet-500
            "#ec4899",  # pink-500
            "#06b6d4",  # cyan-500
            "#f97316",  # orange-500
            "#84cc16",  # lime-500
            "#6366f1",  # indigo-500
            "#a855f7",  # purple-500
            "#14b8a6",  # teal-500
        ]
        return palette[team_id % len(palette)]

    def _get_table(self, cache, name):
        """Helper to retrieve a table from cache with case-insensitive key lookup."""
        if not cache:
            return []

        # Try direct lookup first (most common)
        if name in cache:
            return cache[name]

        # Try lowercase lookup (normalized by MmToJsonConverter)
        lower_name = name.lower()
        if lower_name in cache:
            return cache[lower_name]

        # Exhaustive case-insensitive search
        for actual_key in cache.keys():
            if actual_key.lower() == lower_name:
                return cache[actual_key]

        return []

    def GetMeets(self, request, context):
        request = request or pb2.GetMeetsRequest()
        cache, _ = self._load_user_data(context)
        uid = self._check_auth(context)

        data = self._get_table(cache, "meet")

        if not data and cache:
            logging.warning(f"GetMeets: No 'meet' table found for {uid}. Available tables: {list(cache.keys())}")

        meets = []
        for item in data:
            # Universal case-insensitive field lookup
            def get_field(d, keys):
                if not d:
                    return None
                for k in keys:
                    if k in d:
                        return d[k]
                    for actual_key in d.keys():
                        if actual_key.lower() == k.lower():
                            return d[actual_key]
                return None

            name = get_field(item, ["meet_name1", "meet_name", "mname", "Meet_name1"]) or "Unknown Meet"
            loc = get_field(item, ["location", "meet_location", "Meet_location"])
            start = self._format_date(get_field(item, ["start", "start_date", "meet_start", "Meet_start"]))
            end = self._format_date(get_field(item, ["end", "end_date", "meet_end", "Meet_end"]))
            course_val = get_field(item, ["course", "meet_course", "Meet_course"])

            meets.append(
                pb2.Meet(
                    id="1",
                    name=str(name or "Unknown Meet"),
                    location=str(loc or ""),
                    start_date=str(start or ""),
                    end_date=str(end or ""),
                    course=str(course_val or ""),
                    status="active",
                )
            )
        return pb2.GetMeetsResponse(meets=meets)

    def GetTeams(self, request, context):
        request = request or pb2.GetTeamsRequest()
        uid = self._check_auth(context)
        cache, _ = self._load_user_data(context)

        data = self._get_table(cache, "team")
        athletes = self._get_table(cache, "athlete")

        logging.debug(f"DEBUG: GetTeams for user {uid}, found {len(data)} teams")

        # Count athletes per team
        ath_counts: dict[int, int] = {}
        for ath in athletes:
            t_id = self._safe_int(ath.get("team_no", 0))
            ath_counts[t_id] = ath_counts.get(t_id, 0) + 1

        teams = []
        for item in data:
            # Universal case-insensitive field lookup
            def get_field(d, keys):
                if not d:
                    return None
                for k in keys:
                    if k in d:
                        return d[k]
                    for actual_key in d.keys():
                        if actual_key.lower() == k.lower():
                            return d[actual_key]
                return None

            t_id = self._safe_int(get_field(item, ["team_no", "team", "t_id", "Team_no"]))
            teams.append(
                pb2.Team(
                    id=t_id,
                    name=str(get_field(item, ["team_name", "tname", "Team_name"]) or "Unknown"),
                    code=str(get_field(item, ["team_abbr", "tabbr", "Team_abbr"]) or ""),
                    lsc=str(get_field(item, ["team_lsc", "tlsc", "team_lsc"]) or ""),
                    city=str(get_field(item, ["team_city", "tcity", "team_city"]) or ""),
                    state=str(get_field(item, ["team_statenew", "tstate", "team_statenew"]) or ""),
                    athlete_count=ath_counts.get(t_id, 0),
                    color=self._get_team_color(t_id),
                )
            )
        return pb2.GetTeamsResponse(teams=teams)

    def GetTeam(self, request, context):
        request = request or pb2.GetTeamRequest()
        team_id = request.id
        cache, _ = self._load_user_data(context)
        data = cache.get("team", [])
        athlete_data = cache.get("athlete", [])
        athlete_counts: dict[int, int] = {}
        for a in athlete_data:
            t_no = self._safe_int(a.get("team_no"))
            if t_no:
                athlete_counts[t_no] = athlete_counts.get(t_no, 0) + 1

        for item in data:
            if self._safe_int(item.get("team_no", 0)) == team_id:
                return pb2.GetTeamResponse(
                    team=pb2.Team(
                        id=self._safe_int(item.get("team_no", 0)),
                        name=str(item.get("team_name", "Unknown") or "Unknown"),
                        code=str(item.get("team_abbr", "") or ""),
                        lsc=str(item.get("team_lsc", "") or ""),
                        city=str(item.get("team_city", "") or ""),
                        state=str(item.get("team_statenew", "") or ""),
                        athlete_count=athlete_counts.get(team_id, 0),
                        color=self._get_team_color(team_id),
                    )
                )

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Team {team_id} not found")
        return pb2.GetTeamResponse()

    def GetAthletes(self, request, context):
        request = request or pb2.GetAthletesRequest()
        cache, _ = self._load_user_data(context)
        data = cache.get("athlete", [])
        teams_map = {self._safe_int(t.get("team_no", 0)): t.get("team_name") for t in cache.get("team", [])}

        athletes = []
        for item in data:
            t_id = self._safe_int(item.get("team_no", 0))
            if request and request.team_id and str(t_id) != request.team_id:
                continue

            dob_raw = item.get("ath_birthdate") or item.get("birth_date") or ""
            # dob_raw could be a pandas Timestamp, cast to string
            dob = str(dob_raw).split(" ")[0] if dob_raw else ""

            athletes.append(
                pb2.Athlete(
                    id=self._safe_int(item.get("ath_no", 0)),
                    first_name=str(item.get("first_name", "") or ""),
                    last_name=str(item.get("last_name", "") or ""),
                    gender=str(item.get("ath_sex", "") or ""),
                    age=self._safe_int(item.get("ath_age", 0)),
                    team_id=t_id,
                    team_name=str(teams_map.get(t_id, "Unknown") or "Unknown"),
                    school_year=str(item.get("school_yr", "") or ""),
                    reg_no=str(item.get("reg_no", "") or ""),
                    date_of_birth=str(dob or ""),
                )
            )
        return pb2.GetAthletesResponse(athletes=athletes)

    def GetAthlete(self, request, context):
        request = request or pb2.GetAthleteRequest()
        ath_id = request.id
        cache, _ = self._load_user_data(context)
        data = cache.get("athlete", [])
        teams_map = {self._safe_int(t.get("team_no", 0)): t.get("team_name") for t in cache.get("team", [])}

        for item in data:
            if self._safe_int(item.get("ath_no", 0)) == ath_id:
                t_id = self._safe_int(item.get("team_no", 0))
                return pb2.GetAthleteResponse(
                    athlete=pb2.Athlete(
                        id=self._safe_int(item.get("ath_no", 0)),
                        first_name=str(item.get("first_name", "") or ""),
                        last_name=str(item.get("last_name", "") or ""),
                        gender=str(item.get("ath_sex", "") or ""),
                        age=self._safe_int(item.get("ath_age", 0)),
                        team_id=t_id,
                        team_name=str(teams_map.get(t_id, "Unknown") or "Unknown"),
                        school_year=str(item.get("school_yr", "") or ""),
                        reg_no=str(item.get("reg_no", "") or ""),
                    )
                )

        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details(f"Athlete {ath_id} not found")
        return pb2.GetAthleteResponse()

    def GetEvents(self, request, context):
        request = request or pb2.GetEventsRequest()
        cache, _ = self._load_user_data(context)
        data = self._get_table(cache, "event")
        events = []
        stroke_map = {"A": "Freestyle", "B": "Backstroke", "C": "Breast", "D": "Butterfly", "E": "IM"}
        gender_map = {"B": "Boys", "G": "Girls", "X": "Mixed", "M": "Men", "W": "Women", "F": "Women"}

        entry_counts: dict[str, int] = {}
        entries = self._get_table(cache, "entry")
        for e in entries:
            evt_ptr = e.get("event_ptr")
            if evt_ptr:
                entry_counts[str(evt_ptr)] = entry_counts.get(str(evt_ptr), 0) + 1

        relays = self._get_table(cache, "relay")
        for r in relays:
            evt_ptr = r.get("event_ptr")
            if evt_ptr:
                entry_counts[str(evt_ptr)] = entry_counts.get(str(evt_ptr), 0) + 1

        # Build session mapping from Sessitem (Linking Event_ptr to Session No)
        sess_map = {}
        sessitem_table = self._get_table(cache, "sessitem")
        session_table = self._get_table(cache, "session")

        # ptr_to_no: Sess_ptr -> Sess_no
        ptr_to_no = {s.get("sess_ptr"): self._safe_int(s.get("sess_no", 1)) for s in session_table if s.get("sess_ptr")}

        for si in sessitem_table:
            e_ptr = si.get("event_ptr")
            s_ptr = si.get("sess_ptr")
            if e_ptr and s_ptr:
                sess_map[str(e_ptr)] = ptr_to_no.get(s_ptr, 1)

        for item in data:
            # Universal case-insensitive field lookup
            def get_field(d, keys):
                if not d:
                    return None
                for k in keys:
                    if k in d:
                        return d[k]
                    for actual_key in d.keys():
                        if actual_key.lower() == k.lower():
                            return d[actual_key]
                return None

            raw_stroke = str(get_field(item, ["event_stroke"]) or "").upper().strip()
            stroke_desc = stroke_map.get(raw_stroke, raw_stroke)

            is_relay = str(get_field(item, ["ind_rel"]) or "").upper().strip() == "R"
            if raw_stroke == "E" and is_relay:
                stroke_desc = "Medley Relay"
            elif is_relay and stroke_desc != raw_stroke:
                stroke_desc += " Relay"

            raw_gender = str(get_field(item, ["event_sex"]) or "").upper().strip()
            gender_desc = gender_map.get(raw_gender, raw_gender)

            evt_ptr_val = get_field(item, ["event_ptr"]) or get_field(item, ["event_no"]) or "0"
            evt_ptr_int = self._safe_int(evt_ptr_val)
            evt_no = self._safe_int(get_field(item, ["event_no"]))
            dist = self._safe_int(get_field(item, ["event_dist"]))

            low_age = self._safe_int(get_field(item, ["low_age"]))
            high_age = self._safe_int(get_field(item, ["high_age"]))
            age_group = self._format_age(low_age, high_age)

            events.append(
                pb2.Event(
                    id=evt_ptr_int,
                    event_no=evt_no,
                    name=f"{gender_desc} {age_group} {dist} {stroke_desc}",
                    distance=dist,
                    stroke=stroke_desc,
                    gender=gender_desc,
                    age_group=age_group,
                    is_relay=is_relay,
                    entry_count=entry_counts.get(str(evt_ptr_val), 0),
                    session=sess_map.get(str(evt_ptr_val), 1),
                )
            )
        return pb2.GetEventsResponse(events=events)

    def GetEntries(self, request, context):
        request = request or pb2.GetEntriesRequest()
        cache, _ = self._load_user_data(context)
        entries_data = self._get_table(cache, "entry")

        athletes = {self._safe_int(a.get("ath_no")): a for a in self._get_table(cache, "athlete")}
        teams = {self._safe_int(t.get("team_no")): t for t in self._get_table(cache, "team")}
        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {"B": "Boys", "G": "Girls", "X": "Mixed", "M": "Men", "W": "Women", "F": "Women"}

        for e in self._get_table(cache, "event"):
            # Universal case-insensitive field lookup
            def get_field_inner(d, keys):
                if not d:
                    return None
                for k in keys:
                    if k in d:
                        return d[k]
                    for actual_key in d.keys():
                        if actual_key.lower() == k.lower():
                            return d[actual_key]
                return None

            e_ptr = get_field_inner(e, ["event_ptr"]) or get_field_inner(e, ["event_no"])
            if e_ptr:
                g = gender_map.get(str(get_field_inner(e, ["event_sex"]) or "").strip(), "")
                d = get_field_inner(e, ["event_dist"]) or ""
                s = stroke_map.get(str(get_field_inner(e, ["event_stroke"]) or "").strip(), "")
                low = self._safe_int(get_field_inner(e, ["low_age"]))
                high = self._safe_int(get_field_inner(e, ["high_age"]))
                age_group = self._format_age(low, high)
                name = f"{g} {age_group} {d} {s}"
                events_map[str(e_ptr)] = name

        result = []
        for idx, item in enumerate(entries_data):
            # Universal case-insensitive field lookup
            def get_field_inner(d, keys):
                if not d:
                    return None
                for k in keys:
                    if k in d:
                        return d[k]
                    for actual_key in d.keys():
                        if actual_key.lower() == k.lower():
                            return d[actual_key]
                return None

            ath_id = self._safe_int(get_field_inner(item, ["ath_no"]))
            if request and request.athlete_id and str(ath_id) != request.athlete_id:
                continue

            athlete = athletes.get(ath_id, {})
            t_id = self._safe_int(get_field_inner(athlete, ["team_no", "team_no"]))
            team_obj = teams.get(t_id, {})

            event_id_val = get_field_inner(item, ["event_ptr"]) or get_field_inner(item, ["event_no"])
            event_id_int = self._safe_int(event_id_val)
            if request and request.event_id and str(event_id_val) != request.event_id:
                continue

            seed = get_field_inner(item, ["actualseed_time", "convseed_time", "seed_time"])

            entry_id_val = get_field_inner(item, ["entry_no"])
            final_id = self._safe_int(entry_id_val) if entry_id_val else idx

            result.append(
                pb2.Entry(
                    id=final_id,
                    athlete_id=ath_id,
                    event_id=event_id_int,
                    team_id=t_id,
                    seed_time=self._format_time(seed),
                    final_time=self._format_time(get_field_inner(item, ["fin_time", "pre_time"])),
                    place=self._safe_int(get_field_inner(item, ["fin_place", "place"])),
                    event_name=events_map.get(str(event_id_val), f"Event {event_id_val}"),
                    athlete_name=f"{athlete.get('first_name', '')} {athlete.get('last_name', '')}".strip()
                    or "Unknown Athlete",
                    team_name=str(get_field_inner(team_obj, ["team_name", "tname"]) or ""),
                    heat=self._safe_int(get_field_inner(item, ["fin_heat", "pre_heat"])),
                    lane=self._safe_int(get_field_inner(item, ["fin_lane", "pre_lane"])),
                    points=self._safe_float(get_field_inner(item, ["ev_score"])),
                    team_color=self._get_team_color(t_id),
                    status=str(get_field_inner(item, ["fin_stat", "pre_stat"]) or ""),
                )
            )
        return pb2.GetEntriesResponse(entries=result)

    def ListDatasets(self, request, context):
        request = request or pb2.ListDatasetsRequest()
        uid = self._check_auth(context)
        config = self._load_user_config(context)
        active_file = config.get("active_dataset", SOURCE_FILE)

        logging.info(f"ListDatasets: uid={uid}, active_file={active_file}")
        datasets = []
        try:
            # List files from users/[uid]/
            user_prefix = os.path.join("users", uid)
            if hasattr(self.storage, "_get_full_path"):
                full_path = self.storage._get_full_path(user_prefix)
                logging.info(f"ListDatasets: Checking local path: {full_path}")

            # Retry loop for eventual consistency in CI environments            files = []
            for attempt in range(5):
                files = self.storage.list_files(user_prefix)
                if files:
                    break
                if attempt < 4:
                    logging.info(f"ListDatasets: No files found for {uid}, retrying in 2s...")
                    time.sleep(2)

            logging.info(f"ListDatasets: Found {len(files)} files in {user_prefix}: {files}")

            # Also include default Sample_Data.json if it exists and user has no files?
            # For simplicity, let's just list user's files

            for rel_path in files:
                filename = os.path.basename(rel_path)
                # Only allow MDB files or specific data JSONs (not config.json)
                if filename.lower().endswith(".mdb") or (
                    filename.lower().endswith(".json") and filename != "config.json"
                ):
                    # We don't easily get mod time from all storage providers without extra calls
                    # For local, it's easy. For GCS, we need blob.updated.
                    # For now, placeholder or 0
                    mod_time = "0"
                    is_active = filename == active_file
                    datasets.append(pb2.Dataset(filename=filename, is_active=is_active, last_modified=mod_time))

            # Always include Sample_Data.json if nothing else
            if not datasets and self.storage.exists(SOURCE_FILE):
                datasets.append(
                    pb2.Dataset(filename=SOURCE_FILE, is_active=(active_file == SOURCE_FILE), last_modified="0")
                )

        except Exception as e:
            logging.error(f"Error listing datasets: {e}")

        return pb2.ListDatasetsResponse(datasets=datasets)

    def SetActiveDataset(self, request, context):
        request = request or pb2.SetActiveDatasetRequest()
        uid = self._check_auth(context)
        filename = os.path.basename(request.filename)

        if not (filename.endswith(".mdb") or filename.endswith(".json")):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Invalid file type")
            return pb2.SetActiveDatasetResponse()

        user_path = os.path.join("users", uid, filename)
        if not self.storage.exists(user_path) and not (filename == SOURCE_FILE and self.storage.exists(SOURCE_FILE)):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"File {filename} not found.")
            return pb2.SetActiveDatasetResponse()

        with self._lock:
            logging.info(f"Switching user {uid} dataset to {filename}...")
            # Update config
            config = self._load_user_config(context)
            config["active_dataset"] = filename
            self._save_user_config(context, config)

            # Invalidate cache to force reload
            if uid in self._user_cache:
                del self._user_cache[uid]

            # FORCE FS SYNC for E2E consistency
            if hasattr(os, "sync"):
                os.sync()

            # FORCE SYNCHRONOUS EXTRACTION:
            # This ensures the database is fully populated before returning to the caller.
            # Critical for E2E/CI reliability.
            logging.info(f"SetActiveDataset: Forcing synchronous extraction for {uid}/{filename}...")
            try:
                self._load_user_data(context)
                # Clear cache AGAIN after extraction if it's an E2E-like environment
                # to ensure subsequent calls also bypass any race-condition cache entries.
                metadata = dict(context.invocation_metadata() if context else [])
                if os.getenv("IS_E2E") == "true" or "x-e2e-uid" in metadata or "x-user-id" in metadata:
                    if uid in self._user_cache:
                        del self._user_cache[uid]
                logging.info(f"SetActiveDataset: Extraction complete for {uid}/{filename}")
            except Exception as e:
                logging.error(f"SetActiveDataset: Extraction failed for {uid}/{filename}: {e}")

        return pb2.SetActiveDatasetResponse()

    def ClearDataset(self, request, context):
        request = request or pb2.ClearDatasetRequest()
        uid = self._check_auth(context)
        filename = os.path.basename(request.filename)
        if not (filename.endswith(".mdb") or filename.endswith(".json")):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Invalid file type")
            return pb2.ClearDatasetResponse()

        user_path = os.path.join("users", uid, filename)
        if not self.storage.exists(user_path):
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"File {filename} not found.")
            return pb2.ClearDatasetResponse()

        try:
            self.storage.delete_file(user_path)
            config = self._load_user_config(context)
            if config.get("active_dataset") == filename:
                config["active_dataset"] = SOURCE_FILE
                self._save_user_config(context, config)

        except Exception as e:
            logging.error(f"Error deleting dataset {filename}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to delete file: {str(e)}")

        return pb2.ClearDatasetResponse()

    def ClearAllDatasets(self, request, context):
        request = request or pb2.ClearAllDatasetsRequest()
        uid = self._check_auth(context)
        try:
            user_prefix = os.path.join("users", uid)
            files = self.storage.list_files(user_prefix)
            for rel_path in files:
                filename = os.path.basename(rel_path)
                if filename == CONFIG_FILE:
                    continue
                if filename.endswith(".mdb") or filename.endswith(".json"):
                    self.storage.delete_file(rel_path)

            config = self._load_user_config(context)
            config["active_dataset"] = SOURCE_FILE
            self._save_user_config(context, config)

        except Exception as e:
            logging.error(f"Error clearing datasets: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to clear datasets: {str(e)}")

        return pb2.ClearAllDatasetsResponse()

    def _format_date(self, date_str):
        if not date_str:
            return ""
        try:
            date_str = str(date_str).strip()
            if " " in date_str:
                date_str = date_str.split(" ")[0]

            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%y"):
                try:
                    dt = datetime.datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return date_str
        except Exception:
            return str(date_str)

    def GetRelays(self, request, context):
        request = request or pb2.GetRelaysRequest()
        cache, _ = self._load_user_data(context)
        relays_data = cache.get("relay", [])

        relay_names_data = cache.get("relaynames", [])
        relay_legs_map: dict[tuple[Any, Any, Any], list[Any]] = {}
        for rn in relay_names_data:
            key = (rn.get("event_ptr"), self._safe_int(rn.get("team_no")), self._safe_int(rn.get("relay_no")))
            if key not in relay_legs_map:
                relay_legs_map[key] = []
            relay_legs_map[key].append(rn)

        teams = {self._safe_int(t.get("team_no")): t.get("team_name") for t in cache.get("team", [])}
        athletes = {self._safe_int(a.get("ath_no")): a for a in cache.get("athlete", [])}

        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {"B": "Boys", "G": "Girls", "X": "Mixed", "M": "Men", "W": "Women", "F": "Women"}

        for e in cache.get("event", []):
            e_no = e.get("event_no") or e.get("event_ptr")
            if e_no:
                g = gender_map.get(e.get("event_sex", "").strip(), e.get("event_sex", ""))
                d = e.get("event_dist", "")
                s = stroke_map.get(e.get("event_stroke", "").strip(), e.get("event_stroke", ""))
                age_group = self._format_age(e.get("low_age"), e.get("high_age"))
                name = f"{g} {age_group} {d} {s}"
                events_map[e_no] = name

        result = []
        for idx, item in enumerate(relays_data):
            event_ptr = item.get("event_ptr")
            if request and request.event_id and str(event_ptr) != request.event_id:
                continue

            t_id = self._safe_int(item.get("team_ptr") or item.get("team_no") or 0)
            relay_no = self._safe_int(item.get("relay_no"))

            legs = relay_legs_map.get((event_ptr, t_id, relay_no), [])
            legs.sort(key=lambda x: self._safe_int(x.get("pos_no"), 99))

            leg_names = ["", "", "", ""]
            for leg in legs:
                try:
                    pos = self._safe_int(leg.get("pos_no", 0))
                    if 1 <= pos <= 4:
                        ath_id = self._safe_int(leg.get("ath_no"))
                        ath = athletes.get(ath_id)
                        if ath:
                            leg_names[pos - 1] = f"{ath.get('first_name', '')} {ath.get('last_name', '')}"
                except (ValueError, TypeError):
                    continue

            seed = item.get("actualseed_time") or item.get("convseed_time") or item.get("seed_time")

            result.append(
                pb2.Relay(
                    id=idx,
                    event_id=self._safe_int(item.get("event_ptr")),
                    team_id=self._safe_int(t_id),
                    team_name=str(teams.get(t_id, "Unknown") or "Unknown"),
                    leg1_name=str(leg_names[0] or ""),
                    leg2_name=str(leg_names[1] or ""),
                    leg3_name=str(leg_names[2] or ""),
                    leg4_name=str(leg_names[3] or ""),
                    seed_time=self._format_time(seed),
                    final_time=self._format_time(item.get("fin_time")),
                    place=self._safe_int(item.get("fin_place") or item.get("place")),
                    event_name=str(events_map.get(event_ptr, f"Event {event_ptr}") or ""),
                    relay_letter=str(item.get("team_ltr") or ""),
                    heat=self._safe_int(item.get("fin_heat")),
                    lane=self._safe_int(item.get("fin_lane")),
                    team_color=self._get_team_color(t_id),
                    status=str(item.get("fin_stat") or item.get("pre_stat") or ""),
                )
            )
        return pb2.GetRelaysResponse(relays=result)

    def GetScores(self, request, context):
        request = request or pb2.GetScoresRequest()
        cache, config = self._load_user_data(context)

        # Universal case-insensitive field lookup helper
        def get_field(d, keys):
            if not d:
                return None
            for k in keys:
                if k in d:
                    return d[k]
                for actual_key in d.keys():
                    if actual_key.lower() == k.lower():
                        return d[actual_key]
            return None

        teams_data = self._get_table(cache, "team")
        teams = {
            self._safe_int(get_field(t, ["team_no"])): {
                "name": str(get_field(t, ["team_name", "tname", "Team_name"]) or "Unknown"),
                "id": self._safe_int(get_field(t, ["team_no"])),
            }
            for t in teams_data
        }
        scores = {t_id: {"ind": 0.0, "rel": 0.0} for t_id in teams}

        entries_data = self._get_table(cache, "entry")
        athletes = {self._safe_int(get_field(a, ["ath_no"])): a for a in self._get_table(cache, "athlete")}
        events_sex_map = {
            str(get_field(e, ["event_no"]) or get_field(e, ["event_ptr"]) or ""): str(
                get_field(e, ["event_sex"]) or "M"
            ).strip()
            for e in self._get_table(cache, "event")
        }

        if entries_data:
            for e in entries_data:
                ath_id = self._safe_int(get_field(e, ["ath_no"]))
                ath = athletes.get(ath_id)
                if ath:
                    t_id = self._safe_int(get_field(ath, ["team_no"]))
                    if t_id in scores:
                        e_id = str(get_field(e, ["event_ptr"]) or "")
                        sex = events_sex_map.get(e_id, str(get_field(ath, ["ath_sex"]) or "M"))
                        val = self._calculate_points(e, sex, False, cache)
                        scores[t_id]["ind"] += val

        relays_data = self._get_table(cache, "relay")
        if relays_data:
            for r in relays_data:
                t_id = self._safe_int(get_field(r, ["team_no"]))
                if not t_id or t_id == "0":
                    t_id = self._safe_int(get_field(r, ["team_ptr"]))

                if t_id in scores:
                    e_id = str(get_field(r, ["event_ptr"]) or "")
                    sex = events_sex_map.get(e_id, str(get_field(r, ["rel_sex"]) or "X"))
                    val = self._calculate_points(r, sex, True, cache)
                    scores[t_id]["rel"] += val

        meets = self._get_table(cache, "meet")
        meet_name = config.get("meet_name")
        if not meet_name and meets:
            m = meets[0]
            meet_name = get_field(m, ["meet_name1", "meet_name", "mname"])

        result = []
        for t_id, s in scores.items():
            total = s["ind"] + s["rel"]
            result.append(
                pb2.Score(
                    team_id=t_id,
                    team_name=teams[t_id]["name"],
                    individual_points=s["ind"],
                    relay_points=s["rel"],
                    total_points=total,
                    rank=0,
                    meet_name=str(meet_name or "Unknown Meet"),
                )
            )

        result.sort(key=lambda x: x.total_points, reverse=True)
        for i, r in enumerate(result):
            if r.total_points > 0:
                r.rank = i + 1

        return pb2.GetScoresResponse(scores=result)

    def _get_scoring_map(self, cache):
        scoring_data = cache.get("scoring", [])
        scoring_map: dict[str, dict[str, dict[int, dict[str, float]]]] = {}
        for row in scoring_data:
            div = str(row.get("score_divno", "0"))
            sex = row.get("score_sex", "M").upper()
            place = self._safe_int(row.get("score_place", 0))

            if div not in scoring_map:
                scoring_map[div] = {}
            if sex not in scoring_map[div]:
                scoring_map[div][sex] = {}

            scoring_map[div][sex][place] = {
                "ind": self._safe_float(row.get("ind_score", 0)),
                "rel": self._safe_float(row.get("rel_score", 0)),
            }
        return scoring_map

    def _format_age(self, low, high):
        """Standardize age group naming (e.g., 6 & under)."""
        low = self._safe_int(low)
        high = self._safe_int(high)
        if low == 0 and high >= 109:
            return "Open"
        if low == 0:
            return f"{high} & under"
        if high >= 109:
            return f"{low} & over"
        return f"{low}-{high}"

    def _calculate_points(self, item, sex, is_relay, cache):
        score = self._safe_float(item.get("ev_score", 0))
        if score > 0:
            return score

        place = self._safe_int(item.get("fin_place", item.get("place", 0)))
        if place <= 0:
            return 0.0

        div = str(item.get("div_no", "0"))
        sex_map = {"B": "M", "M": "M", "G": "F", "W": "F", "F": "F", "X": "M"}
        mapped_sex = sex_map.get(sex.upper(), "M")

        scoring_map = self._get_scoring_map(cache)
        div_map = scoring_map.get(div, scoring_map.get("0", {}))
        sex_scores = div_map.get(mapped_sex, div_map.get("M", {}))

        score_data = sex_scores.get(place, {})
        return score_data.get("rel" if is_relay else "ind", 0.0)

    def GetEventScores(self, request, context):
        request = request or pb2.GetEventScoresRequest()
        cache, _ = self._load_user_data(context)
        entries = self._get_table(cache, "entry")
        relays = self._get_table(cache, "relay")
        athletes_map = {self._safe_int(a.get("ath_no")): a for a in self._get_table(cache, "athlete")}
        teams_map = {self._safe_int(t.get("team_no")): t.get("team_name") for t in self._get_table(cache, "team")}

        # Universal case-insensitive field lookup helper
        def get_field(d, keys):
            if not d:
                return None
            for k in keys:
                if k in d:
                    return d[k]
                for actual_key in d.keys():
                    if actual_key.lower() == k.lower():
                        return d[actual_key]
            return None

        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {"B": "Boys", "G": "Girls", "X": "Mixed", "M": "Men", "W": "Women", "F": "Women"}

        event_dict: dict[str, dict[str, Any]] = {}
        event_raw_map = {}

        for e in self._get_table(cache, "event"):
            e_no = get_field(e, ["event_no"]) or get_field(e, ["event_ptr"])
            if not e_no:
                continue

            event_raw_map[str(e_no)] = e
            g = gender_map.get(str(get_field(e, ["event_sex"]) or "").strip(), "")
            d = get_field(e, ["event_dist"]) or ""
            s_raw = str(get_field(e, ["event_stroke"]) or "").strip()
            s = stroke_map.get(s_raw, s_raw)

            is_relay = str(get_field(e, ["ind_rel"]) or "").upper().strip() == "R"
            if s_raw == "E" and is_relay:
                s = "Medley Relay"
            elif is_relay and s != s_raw:
                s += " Relay"

            low = get_field(e, ["low_age"])
            high = get_field(e, ["high_age"])
            age_group = self._format_age(low, high)
            name = f"{g} {age_group} {d} {s}"
            events_map[str(e_no)] = name
            event_dict[str(e_no)] = {"id": self._safe_int(e_no), "name": name, "entries": []}

        for item in entries:
            e_id = str(get_field(item, ["event_ptr"]) or "")
            if e_id not in event_dict:
                continue

            ath_id = self._safe_int(get_field(item, ["ath_no"]))
            ath = athletes_map.get(ath_id)
            t_id = self._safe_int(get_field(ath, ["team_no"])) if ath else 0
            place = self._safe_int(get_field(item, ["fin_place", "place"]))

            ev_raw = event_raw_map.get(e_id, {})
            points = self._calculate_points(item, str(get_field(ev_raw, ["event_sex"]) or "M"), False, cache)

            if not get_field(item, ["fin_time"]) and place <= 0:
                continue

            seed = get_field(item, ["actualseed_time", "convseed_time", "seed_time"])

            entry_obj = pb2.Entry(
                id=0,
                event_id=self._safe_int(e_id),
                athlete_id=ath_id,
                athlete_name=f"{ath.get('first_name', '')} {ath.get('last_name', '')}" if ath else "Unknown",
                team_id=t_id,
                team_name=str(teams_map.get(t_id, "Unknown")),
                seed_time=self._format_time(seed),
                final_time=self._format_time(get_field(item, ["fin_time"])),
                place=place,
                points=points,
                event_name=events_map.get(e_id, ""),
            )
            event_dict[e_id]["entries"].append(entry_obj)

        for item in relays:
            e_id = str(get_field(item, ["event_ptr"]) or "")
            if e_id not in event_dict:
                continue

            t_id = self._safe_int(get_field(item, ["team_ptr", "team_no"]))
            place = self._safe_int(get_field(item, ["fin_place", "place"]))
            rel_ltr = get_field(item, ["team_ltr"]) or ""

            ev_raw = event_raw_map.get(e_id, {})
            points = self._calculate_points(item, str(get_field(ev_raw, ["event_sex"]) or "X"), True, cache)

            if not item.get("fin_time") and place <= 0:
                continue

            seed = item.get("actualseed_time") or item.get("convseed_time") or item.get("seed_time")

            entry_obj = pb2.Entry(
                id=0,
                event_id=self._safe_int(e_id),
                athlete_id=0,
                athlete_name=f"Relay Team ({rel_ltr})" if rel_ltr else "Relay Team",
                team_id=t_id,
                team_name=teams_map.get(t_id, "Unknown"),
                seed_time=self._format_time(seed),
                final_time=self._format_time(item.get("fin_time")),
                place=place,
                points=points,
                heat=self._safe_int(item.get("fin_heat", 0)),
                lane=self._safe_int(item.get("fin_lane", 0)),
                event_name=events_map.get(e_id, ""),
            )
            event_dict[e_id]["entries"].append(entry_obj)

        resp_list = []
        sorted_keys = sorted(event_dict.keys(), key=lambda k: int(k))
        for k in sorted_keys:
            ev = event_dict[k]
            ev["entries"].sort(key=lambda x: x.place if x.place > 0 else 9999)

            resp_list.append(pb2.EventScore(event_id=ev["id"], event_name=ev["name"], entries=ev["entries"]))

        return pb2.GetEventScoresResponse(event_scores=resp_list)

    def GenerateReport(self, request, context):
        request = request or pb2.GenerateReportRequest()
        try:
            # Support unauthenticated access for Sample_Data.json (for dev/debug)
            # Otherwise require authentication
            try:
                # We must NOT use _check_auth here because it aborts immediately.
                uid = getattr(context, "uid", None)
                if uid is None and context:
                    # If no uid in context, check for metadata override (E2E)
                    try:
                        metadata = dict(context.invocation_metadata())
                        uid = metadata.get("x-user-id")
                    except Exception:
                        pass

                if uid is None:
                    # Still no UID, check if it's local or auth disabled
                    if os.getenv("GRPC_AUTH_DISABLED") == "true" or not os.getenv("K_SERVICE"):
                        uid = "dev-user"

                if uid:
                    cache, _ = self._load_user_data(context)
                else:
                    raise ValueError("No authentication")
            except Exception:
                # Fallback to Sample_Data if no auth provided
                sample_path = os.path.join(os.path.dirname(__file__), "..", "data", SOURCE_FILE)
                with open(sample_path) as f:
                    cache = json.load(f)
            rtype_map = {
                pb2.REPORT_TYPE_PSYCH_UNSPECIFIED: "psych",
                pb2.REPORT_TYPE_ENTRIES: "entries",
                pb2.REPORT_TYPE_LINEUPS: "lineups",
                pb2.REPORT_TYPE_RESULTS: "results",
                pb2.REPORT_TYPE_MEET_PROGRAM: "program",
                pb2.REPORT_TYPE_MEET_PROGRAM_HTML: "program_html",
                pb2.REPORT_TYPE_ENTRIES_HYTEK: "entries_hytek",
                pb2.REPORT_TYPE_ENTRIES_CLUB: "entries_club",
                pb2.REPORT_TYPE_LANE_TIMER_SHEETS: "lane_timer_sheets",
                pb2.REPORT_TYPE_JUDGE_SHEETS: "judge_sheets",
            }

            from mm_to_json.mm_to_json import MmToJsonConverter

            # Convert data once
            converter = MmToJsonConverter(table_data=cache)
            full_data = converter.convert()

            # Serialize to msgpack for worker access
            with tempfile.NamedTemporaryFile(suffix=".msgpack", delete=False) as msgpack_tmp:
                msgpack_path = msgpack_tmp.name
                msgpack.pack({"full_data": full_data, "cache": cache}, msgpack_tmp, default=msgpack_encode)

            try:
                res = _process_single_report_process(
                    request.type,
                    request.title,
                    request.team_filter,
                    request.gender_filter,
                    request.age_group_filter,
                    uid,
                    request.columns_on_page if request.HasField("columns_on_page") else 2,
                    request.show_relay_swimmers if request.HasField("show_relay_swimmers") else True,
                    request.zebra_striping if request.HasField("zebra_striping") else False,
                    msgpack_path,
                    rtype_map,
                    request.renderer_type if hasattr(request, "renderer_type") else None,
                    getattr(request, "html_preview", False),
                )
            finally:
                # Cleanup msgpack file
                if os.path.exists(msgpack_path):
                    os.remove(msgpack_path)

            if not res["success"]:
                logging.error(f"Report generation failed in worker: {res.get('error')}")
                return pb2.GenerateReportResponse(success=False, message=res["error"])

            pdf_bytes = res["content"] if res["filename"].endswith(".pdf") else b""
            html_str = res["content"].decode("utf-8") if res["filename"].endswith(".html") else ""

            logging.info(
                f"Report generated: {res['filename']} (PDF: {len(pdf_bytes)} bytes, HTML: {len(html_str)} chars)"
            )

            return pb2.GenerateReportResponse(
                success=True,
                message="Report generated successfully",
                pdf_content=pdf_bytes,
                filename=res["filename"],
                html_content=html_str,
            )

        except Exception as e:
            logging.error(f"Error generating report: {e}")
            return pb2.GenerateReportResponse(success=False, message=str(e))

    def GenerateReportBundle(self, request, context):
        """Asynchronously generates a report bundle."""
        logging.info("GenerateReportBundle RPC called")
        # Support unauthenticated access for Sample_Data.json (for dev/debug)
        # Otherwise require authentication
        try:
            uid = self._check_auth(context)
            if uid:
                cache, _ = self._load_user_data(context)
            else:
                raise ValueError("No authentication")
        except Exception:
            # Fallback to Sample_Data if no auth provided
            # This is safe because Sample_Data is public
            sample_path = os.path.join(os.path.dirname(__file__), "..", "data", SOURCE_FILE)
            with open(sample_path) as f:
                cache = json.load(f)
            uid = "sample-user"

        if request is None:
            return pb2.GenerateReportBundleResponse(success=False, message="Missing request")

        # Create background job
        job_id = self.job_manager.create_job()
        logging.info(f"Created background job {job_id}")

        # Start background thread for generation
        # Note: In Cloud Run, this thread gets CPU while polling requests are active.
        thread = threading.Thread(target=self._run_bundle_generation_job, args=(job_id, request, uid, cache))
        thread.start()

        return pb2.GenerateReportBundleResponse(
            success=True,
            message="Bundle generation started",
            job_id=job_id,
        )

    def _run_bundle_generation_job(self, job_id, request, uid, cache):
        """Background worker for report bundle generation."""
        logging.info(f"Background thread started for job {job_id}")
        try:
            self.job_manager.update_job(job_id, status=pb2.JOB_STATUS_PROCESSING, message="Converting data...")
            logging.info(f"Job {job_id}: starting MmToJsonConverter")
            rtype_map = {
                pb2.REPORT_TYPE_PSYCH_UNSPECIFIED: "psych",
                pb2.REPORT_TYPE_ENTRIES: "entries",
                pb2.REPORT_TYPE_LINEUPS: "lineups",
                pb2.REPORT_TYPE_RESULTS: "results",
                pb2.REPORT_TYPE_MEET_PROGRAM: "program",
                pb2.REPORT_TYPE_MEET_PROGRAM_HTML: "program_html",
                pb2.REPORT_TYPE_ENTRIES_HYTEK: "entries_hytek",
                pb2.REPORT_TYPE_ENTRIES_CLUB: "entries_club",
                pb2.REPORT_TYPE_LANE_TIMER_SHEETS: "lane_timer_sheets",
                pb2.REPORT_TYPE_JUDGE_SHEETS: "judge_sheets",
            }

            # Convert data once in main process
            converter = MmToJsonConverter(table_data=cache)
            full_data = converter.convert()

            num_events = sum(len(s.get("events", [])) for s in full_data.get("sessions", []))
            logging.info(f"Job {job_id}: data conversion complete. {num_events} events found.")

            with tempfile.NamedTemporaryFile(suffix=".msgpack", delete=False) as msgpack_tmp:
                msgpack_path = msgpack_tmp.name
                msgpack.pack({"full_data": full_data, "cache": cache}, msgpack_tmp, default=msgpack_encode)
                msgpack_tmp.flush()
                msgpack_tmp.close()

            tasks = []
            max_workers = 3
            self.job_manager.update_job(job_id, progress=0.05, message=f"Rendering {len(request.reports)} reports...")
            logging.info(f"Job {job_id}: starting ProcessPoolExecutor with {max_workers} workers")

            ctx = multiprocessing.get_context("spawn")
            try:
                # Store report requests for re-mapping results later
                report_reqs = list(request.reports)

                with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as executor:
                    for idx, report_req in enumerate(report_reqs):
                        tasks.append(
                            executor.submit(
                                _process_single_report_process,
                                report_req.type,
                                report_req.title,
                                report_req.team_filter,
                                report_req.gender_filter,
                                report_req.age_group_filter,
                                uid,
                                report_req.columns_on_page if getattr(report_req, "columns_on_page", None) else 2,
                                report_req.show_relay_swimmers if report_req.HasField("show_relay_swimmers") else True,
                                report_req.zebra_striping if report_req.HasField("zebra_striping") else False,
                                msgpack_path,
                                rtype_map,
                                request.renderer_type if hasattr(request, "renderer_type") else None,
                                False,  # html_preview
                                idx,
                            )
                        )

                # PROGRESS TRACKING: Update as each task completes (unordered)
                from concurrent.futures import as_completed

                total_reports = len(tasks)
                finished_count = 0

                # We still need to wait for all results and gather them
                # But we can update progress immediately as they finish
                for _ in as_completed(tasks):
                    finished_count += 1
                    progress = 0.05 + (0.90 * (finished_count / total_reports))
                    self.job_manager.update_job(
                        job_id, progress=progress, message=f"Generated {finished_count}/{total_reports} reports"
                    )
                    logging.info(f"Job {job_id}: Progress update {finished_count}/{total_reports}")

                # BUNDLING: Create ZIP in original order
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for i, future in enumerate(tasks):
                        res = future.result()
                        if res.get("success"):
                            zip_file.writestr(res["filename"], res["content"])
                            logging.info(
                                f"Job {job_id}: Report {i + 1}/{total_reports} ({res.get('rtype')}) added to bundle"
                            )
                        else:
                            raise Exception(
                                f"Failed to generate report {res.get('idx')} ({res.get('rtype')}): {res['error']}"
                            )
            finally:
                if os.path.exists(msgpack_path):
                    os.remove(msgpack_path)

            self.job_manager.update_job(job_id, message="Uploading bundle...")

            num_reports = len(request.reports)
            bundle_name = (
                request.bundle_name
                or f"meet_bundle_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{num_reports}_items.zip"
            )
            if not bundle_name.endswith(".zip"):
                bundle_name += ".zip"

            bundle_rel_path = os.path.join("users", uid, "published", "bundles", bundle_name)

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as bundle_tmp:
                bundle_tmp.write(zip_buffer.getvalue())
                bundle_tmp_path = bundle_tmp.name
                bundle_tmp.close()

            try:
                self.storage.upload_file(bundle_tmp_path, bundle_rel_path)
            finally:
                if os.path.exists(bundle_tmp_path):
                    os.remove(bundle_tmp_path)

            # Task C: Use Signed URL if available
            bundle_url = self.storage.get_url(bundle_rel_path)

            # Fallback: If get_url returned a relative path (e.g. /api/data?...)
            # or if it's a GCS public URL that isn't signed (missing '?'),
            # ensure it's a full URL using FRONTEND_URL.
            is_relative = bundle_url.startswith("/")
            is_unsigned_gcs = "storage.googleapis.com" in bundle_url and "?" not in bundle_url

            if is_relative or is_unsigned_gcs:
                token = os.getenv("DATA_ACCESS_TOKEN", "mmtools-default-secret-2024")
                import urllib.parse

                safe_bundle_path = urllib.parse.quote(bundle_rel_path)
                # Try to get FRONTEND_URL from environment, defaulting to 3100 for local dev consistency
                frontend_base = os.getenv("FRONTEND_URL", "http://localhost:3100")
                bundle_url = f"{frontend_base}/api/data?path={safe_bundle_path}&token={token}"
                logging.info(f"Using absolute proxy fallback URL: {bundle_url}")

            logging.info(f"Job {job_id}: Final bundle_url: {bundle_url}")

            # ATOMIC UPDATE: Set everything at once to prevent race with poller
            self.job_manager.update_job(
                job_id, status=pb2.JOB_STATUS_COMPLETED, progress=1.0, message="Complete", bundle_url=bundle_url
            )

        except Exception as e:
            logging.error(f"Background job {job_id} failed: {e}")
            self.job_manager.update_job(job_id, status=pb2.JOB_STATUS_FAILED, message=str(e))

    def GetJobStatus(self, request, context):
        """Retrieves the status of a background job."""
        logging.info(f"GetJobStatus RPC called for job_id: {request.job_id}")
        if not request.job_id:
            return pb2.GetJobStatusResponse(status=pb2.JOB_STATUS_FAILED, message="Missing job_id")

        job = self.job_manager.get_job(request.job_id)
        if not job:
            return pb2.GetJobStatusResponse(status=pb2.JOB_STATUS_FAILED, message="Job not found")

        # Ensure we return a string for bundle_url
        b_url = job.get("bundle_url") or ""

        return pb2.GetJobStatusResponse(
            status=job["status"],
            progress=job["progress"],
            message=job["message"],
            bundle_url=b_url,
        )

    def GetSessions(self, request, context):
        request = request or pb2.GetSessionsRequest()
        cache, _ = self._load_user_data(context)
        data = self._get_table(cache, "session")
        meets = self._get_table(cache, "meet")

        # Universal case-insensitive field lookup helper
        def get_field(d, keys):
            if not d:
                return None
            for k in keys:
                if k in d:
                    return d[k]
                for actual_key in d.keys():
                    if actual_key.lower() == k.lower():
                        return d[actual_key]
            return None

        meet_start = None
        if meets:
            m = meets[0]
            date_str = get_field(m, ["start", "start_date"]) or ""
            if date_str:
                try:
                    if " " in date_str:
                        date_str = date_str.split(" ")[0]
                    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d-%b-%y"):
                        try:
                            meet_start = datetime.datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

        # Count events per session for reliability
        sess_item_table = self._get_table(cache, "sessitem")
        event_table = self._get_table(cache, "event")

        # event_counts_map: sess_ptr -> count
        event_counts_map: dict[str, int] = {}
        # sess_no_counts: sess_no -> count (fallback)
        sess_no_counts: dict[int, int] = {}

        for si in sess_item_table:
            s_ptr = get_field(si, ["sess_ptr"])
            if s_ptr:
                event_counts_map[str(s_ptr)] = event_counts_map.get(str(s_ptr), 0) + 1

        for e in event_table:
            s_no = self._safe_int(get_field(e, ["sess_no"])) or 1
            if s_no:
                sess_no_counts[s_no] = sess_no_counts.get(s_no, 0) + 1

        sessions_to_process = []
        if data:
            for item in data:
                s_ptr = get_field(item, ["sess_ptr"])
                s_no = self._safe_int(get_field(item, ["sess_no"]))
                e_cnt = self._safe_int(get_field(item, ["event_cnt"]))

                if not e_cnt:
                    if s_ptr:
                        e_cnt = event_counts_map.get(str(s_ptr), 0)
                    if not e_cnt and s_no:
                        e_cnt = sess_no_counts.get(s_no, 0)

                sessions_to_process.append(
                    {
                        "id": str(s_no or "0"),
                        "name": str(get_field(item, ["sess_name", "sname"]) or f"Session {s_no}"),
                        "day": self._safe_int(get_field(item, ["sess_day", "day"]) or 1),
                        "warmup": self._safe_int(get_field(item, ["sess_warmup"]) or 0),
                        "starttime": self._safe_int(get_field(item, ["sess_starttime"]) or 0),
                        "event_cnt": e_cnt,
                        "source_item": item,
                    }
                )
        else:
            sess_ids = sorted({self._safe_int(get_field(e, ["sess_no"]) or 1) for e in event_table})
            if not sess_ids:
                sess_ids = [1]

            for s_id in sess_ids:
                sessions_to_process.append(
                    {
                        "id": str(s_id),
                        "name": f"Session {s_id}",
                        "day": 1,
                        "warmup": 0,
                        "starttime": 0,
                        "event_cnt": sess_no_counts.get(s_id, 0) if event_table else None,
                        "source_item": {},
                    }
                )

        sessions = []
        for s_info in sessions_to_process:
            item = s_info["source_item"]
            sess_date = ""
            day_offset = self._safe_int(s_info["day"]) - 1
            if meet_start and day_offset >= 0:
                d = meet_start + datetime.timedelta(days=day_offset)
                sess_date = d.strftime("%Y-%m-%d")

            sessions.append(
                pb2.Session(
                    id=str(s_info["id"]),
                    meet_id="1",
                    name=s_info["name"],
                    date=sess_date,
                    warm_up_time=self._seconds_to_time(s_info["warmup"]),
                    start_time=self._seconds_to_time(s_info["starttime"]),
                    event_count=s_info["event_cnt"] or 0,
                    session_num=self._safe_int(s_info["id"]),
                    day=self._safe_int(s_info["day"]),
                )
            )
        return pb2.GetSessionsResponse(sessions=sessions)

    def GetAdminConfig(self, request, context):
        request = request or pb2.GetAdminConfigRequest()
        config = self._load_user_config(context)
        return pb2.GetAdminConfigResponse(
            meet_name=config.get("meet_name", ""), meet_description=config.get("meet_description", "")
        )

    def UpdateAdminConfig(self, request, context):
        request = request or pb2.UpdateAdminConfigRequest()
        self._check_auth(context)
        config = self._load_user_config(context)
        config["meet_name"] = request.meet_name
        config["meet_description"] = request.meet_description
        self._save_user_config(context, config)
        return pb2.UpdateAdminConfigResponse(
            meet_name=config.get("meet_name", ""), meet_description=config.get("meet_description", "")
        )

    def PublishMeetData(self, request, context):
        request = request or pb2.PublishMeetDataRequest()
        uid = self._check_auth(context)
        cache, config = self._load_user_data(context)
        current_file = config.get("active_dataset", SOURCE_FILE)

        try:
            from mm_to_json.judge_app_extractor import JudgeAppExtractor

            converter = MmToJsonConverter(table_data=cache)
            extractor = JudgeAppExtractor(converter)
            judge_data = extractor.extract_judge_data()

            # Save to a user-specific public-accessible location via StorageProvider
            base_filename = current_file
            if base_filename.lower().endswith((".json", ".mdb")):
                base_filename = os.path.splitext(base_filename)[0]

            filename = f"program_{base_filename}.json"
            user_pub_path = os.path.join("users", uid, "published", filename)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                json.dump(judge_data, tmp)
                tmp_path = tmp.name

            try:
                self.storage.upload_file(tmp_path, user_pub_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            # Generate URLs
            # Use the /api/data proxy for the program_url to avoid direct GCS signed URL issues.
            # This works statelessly using the DATA_ACCESS_TOKEN.
            token = os.getenv("DATA_ACCESS_TOKEN", "mmtools-default-secret-2024")

            # Use frontend_url from request if provided, otherwise environment variables
            if request.frontend_url:
                frontend_base = request.frontend_url.rstrip("/")
            else:
                frontend_host = os.getenv("FRONTEND_PUBLIC_HOST", "localhost")
                frontend_port = os.getenv("FRONTEND_PORT", "3000")
                frontend_base = os.getenv("FRONTEND_PUBLIC_URL", f"http://{frontend_host}:{frontend_port}")

            # Correctly path-encode the user_pub_path
            import urllib.parse

            safe_pub_path = urllib.parse.quote(user_pub_path)
            program_url = f"{frontend_base}/api/data?path={safe_pub_path}&token={token}"
            sync_url = f"{frontend_base}/api/sync-dqs?token={token}&uid={uid}"

            logging.info(f"PublishMeetData: frontend_base={frontend_base}, program_url={program_url}")

            # Nested URLs must be fully encoded to be valid as a query parameter value.
            # We use safe="" to ensure EVERYTHING including / and : is encoded for the final link.
            # This is "Double Encoding" because program_url already has safe_pub_path encoded.
            # But the Judge App will decode the query params ONCE, giving it the original program_url.
            encoded_program = urllib.parse.quote(program_url, safe="")
            encoded_sync = urllib.parse.quote(sync_url, safe="")

            # Determine Judge App Base URL
            # Priority:
            # 1. JUDGE_APP_URL env var
            # 2. Local fallback if frontend is on localhost (for E2E)
            # 3. GitHub Pages production fallback
            judge_app_base = os.getenv("JUDGE_APP_URL")
            if not judge_app_base:
                if "localhost" in frontend_base or "127.0.0.1" in frontend_base:
                    # In local dev/E2E, judge app is served by frontend on port 3000
                    # or via mobile-judge-app container on port 8081.
                    # We prefer port 3000 as it's the primary entry point.
                    judge_app_base = "http://localhost:3000/judge"
                else:
                    # Production GitHub Pages
                    judge_app_base = "https://pfisherogden.github.io/MeetManager-Tools/judge"

            judge_app_url = f"{judge_app_base}?program_url={encoded_program}&sync_url={encoded_sync}"
            return pb2.PublishMeetDataResponse(success=True, message="Published", judge_app_url=judge_app_url)
        except Exception as e:
            logging.error(f"Publish failed: {e}")
            return pb2.PublishMeetDataResponse(success=False, message=str(e))

    def SyncDQs(self, request, context):
        # System-level bypass for stateless sync from mobile apps (authenticated by web-client proxy)
        token = os.getenv("DATA_ACCESS_TOKEN")
        uid = request.uid

        logging.info(f"SyncDQs: Received request for UID: {uid}, Payload length: {len(request.dqs_json)}")

        if token and request.access_token == token:
            uid = request.uid
            logging.info(f"SyncDQs: Authenticated via system token for user {uid}")
        else:
            uid = self._check_auth(context)

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
                self.storage.upload_file(tmp_path, user_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            # Update the master database if it's an MDB
            config = self._load_user_config(context)
            active_filename = config.get("active_dataset")
            if active_filename and active_filename.lower().endswith(".mdb"):
                dataset_path = os.path.join("users", uid, active_filename)
                if self.storage.exists(dataset_path):
                    logging.info(f"Syncing DQs to MDB: {dataset_path} for user {uid}")

                    # Download MDB to local temp for writing
                    with tempfile.NamedTemporaryFile(suffix=".mdb", delete=False) as tmp_mdb:
                        tmp_mdb_path = tmp_mdb.name
                        tmp_mdb.close()

                    try:
                        self.storage.download_file(dataset_path, tmp_mdb_path)

                        # Resolve event pointers and relay status from human-readable numbers
                        cache, _ = self._load_user_data(context)
                        event_table = cache.get("event", [])
                        # Map eventNum (human #) to {ptr, is_relay}
                        event_info_map = {}
                        for e in event_table:
                            # event_no is human #, event_ptr is MDB PK
                            # mtevent is PK in Schema B
                            h_num = self._safe_int(e.get("event_no") or e.get("mtevent"))
                            e_ptr = e.get("event_ptr") or e.get("mtevent")
                            # Ind_rel is 'R' for relays in Schema A, 'i_r' in Schema B?
                            is_relay = str(e.get("Ind_rel", e.get("i_r", ""))).upper() == "R"

                            if h_num and e_ptr:
                                event_info_map[h_num] = {"ptr": e_ptr, "is_relay": is_relay}

                        from mm_to_json import mdb_writer

                        db = mdb_writer.open_db(tmp_mdb_path)
                        try:
                            updated_count = 0
                            for dq in dqs:
                                # Mobile app sends id, swimmer_id, event_id, dq_code, notes, heat, lane
                                event_id = dq.get("event_id")
                                athlete_id = dq.get("swimmer_id")
                                dq_code = dq.get("dq_code", "")
                                heat = self._safe_int(dq.get("heat", 0))
                                lane = self._safe_int(dq.get("lane", 0))

                                info = event_info_map.get(self._safe_int(event_id))
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

                            db.close()
                            # Upload updated MDB back to storage
                            self.storage.upload_file(tmp_mdb_path, dataset_path)

                            # Force cache invalidation so Next.js/Web-Client sees the DQ
                            if uid in self._user_cache:
                                del self._user_cache[uid]
                            logging.info(f"Successfully updated {updated_count} entries in MDB for {uid}")
                        finally:
                            try:
                                db.close()
                            except Exception:
                                pass
                    finally:
                        if os.path.exists(tmp_mdb_path):
                            os.remove(tmp_mdb_path)

            logging.info(f"Synced {len(dqs)} DQs for user {uid}")
            return pb2.SyncDQsResponse(success=True, message=f"Synced {len(dqs)} items")
        except Exception as e:
            logging.error(f"Sync failed: {e}")
            return pb2.SyncDQsResponse(success=False, message=str(e))

    def GetFile(self, request, context):
        # Allow unauthenticated access specifically for sample-user paths (public sample data)
        is_sample = request.path.startswith("users/sample-user/")

        if not is_sample:
            # System-level bypass for stateless access
            token = os.getenv("DATA_ACCESS_TOKEN")
            if token and request.token == token:
                # Authorized via system token, skip uid check for the path prefix
                # but we should still validate it's within 'users/'
                if not (request.path.startswith("users/") or request.path == SOURCE_FILE):
                    context.abort(grpc.StatusCode.PERMISSION_DENIED, "Access denied")
            else:
                uid = self._check_auth(context)
                # Verify path starts with users/[uid] or is Sample_Data.json
                if not (request.path.startswith(f"users/{uid}/") or request.path == SOURCE_FILE):
                    context.abort(grpc.StatusCode.PERMISSION_DENIED, "Access denied")

        path = request.path

        if not self.storage.exists(path):
            context.abort(grpc.StatusCode.NOT_FOUND, f"File {path} not found")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.storage.download_file(path, tmp_path)
            with open(tmp_path, "rb") as f:
                content = f.read()

            import mimetypes

            mime_type, _ = mimetypes.guess_type(path)
            if not mime_type:
                mime_type = "application/octet-stream"

            return pb2.GetFileResponse(content=content, mime_type=mime_type)
        except Exception as e:
            logging.error(f"GetFile failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _safe_int(self, value, default=0):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _format_time(self, val):
        if val is None or val == 0 or val == "0" or str(val).strip() == "":
            return "NT"
        try:
            f_val = float(val)
            if f_val == 0:
                return "NT"
            return f"{f_val:.3f}"
        except (ValueError, TypeError):
            return str(val).strip()

    def _seconds_to_time(self, seconds_val):
        try:
            val = int(seconds_val)
            hours = val // 3600
            minutes = (val % 3600) // 60
            period = "AM"
            if hours >= 12:
                period = "PM"
                if hours > 12:
                    hours -= 12
            if hours == 0:
                hours = 12
            return f"{hours}:{minutes:02d} {period}"
        except (ValueError, TypeError):
            return ""


def serve():
    port = os.getenv("PORT", "8080")
    interceptors = [FirebaseAuthInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=interceptors,
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )

    # Add Health Servicer
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    pb2_grpc.add_MeetManagerServiceServicer_to_server(MeetManagerService(), server)

    server.add_insecure_port(f"0.0.0.0:{port}")
    logging.info(f"Server starting on port {port} with AuthInterceptor and Health check...")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    # Configure logging
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Suppress verbose third-party loggers unless explicitly requested
    if log_level_str != "DEBUG":
        logging.getLogger("fontTools").setLevel(logging.WARNING)
        logging.getLogger("weasyprint").setLevel(logging.WARNING)
        logging.getLogger("jpype").setLevel(logging.WARNING)

    serve()
# Triggering fresh CI run with clean lint state
# Triggering fresh CI run with clean lint state
