from __future__ import annotations

import datetime
import http.server
import json
import logging
import multiprocessing
import os
import signal
import sys
import tempfile
import threading
import time
import typing
import uuid
from collections import OrderedDict
from concurrent import futures
from typing import Any

import grpc
from firebase_admin import auth
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from meet_validation import validate_meet_data
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.platform_setup import setup_platform_env
from storage_provider import GCSStorageProvider, LocalStorageProvider, StorageProvider

# Import generated classes
try:
    from meetmanager.v1 import meet_manager_pb2 as pb2
    from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc
except ImportError:
    pb2 = typing.cast(Any, None)
    pb2_grpc = typing.cast(Any, None)

# Configure platform-specific environments
setup_platform_env()

# Configure logging
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)


# Configure logging in local Pacific Time (PT) for California
def pacific_time_converter(secs):
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo("America/Los_Angeles")
        dt = datetime.datetime.fromtimestamp(secs, tz=tz)
        return dt.timetuple()
    except Exception:
        return time.localtime(secs)


logging.Formatter.converter = staticmethod(pacific_time_converter)


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for Cloud Run structured logging."""

    def format(self, record):
        log_record = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
            "time": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


if os.getenv("K_SERVICE"):
    # Running in Cloud Run, use JSON formatting
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(log_level)
else:
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


def _get_user_email(uid: str) -> str | None:
    """Helper to get user email from Firebase for sharing."""
    if uid == "dev-user" or not os.getenv("K_SERVICE"):
        return os.getenv("DEV_USER_EMAIL")
    try:
        user = auth.get_user(uid)
        return user.email
    except Exception as e:
        logging.warning(f"Failed to get email for user {uid}: {e}")
        return None


def _get_data_access_token() -> str:
    """Helper to retrieve the access token, logging an error if fallback is used in production."""
    token = os.getenv("DATA_ACCESS_TOKEN")
    if not token or not token.strip():
        fallback = "mmtools-default-secret-2024"
        if os.getenv("K_SERVICE"):
            logging.error(
                "CRITICAL: DATA_ACCESS_TOKEN is not set in production! Falling back to insecure default secret."
            )
        return fallback
    return token.strip()


class JobManager:
    """Manages the state of background jobs using Firestore if available, otherwise in-memory."""

    in_memory_jobs: dict[str, dict[str, Any]] = {}
    lock = threading.Lock()

    def __init__(self):
        self.use_firestore = False

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
                logging.info(
                    f"JobManager: create_job: added job_id={job_id}, keys={list(self.in_memory_jobs.keys())}, id(in_memory_jobs)={id(self.in_memory_jobs)}"
                )

        return job_id

    def update_job(
        self,
        job_id: str,
        status: int | None = None,
        progress: float | None = None,
        message: str | None = None,
        bundle_url: str | None = None,
        google_sheet_urls: list[str] | None = None,
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
            if google_sheet_urls is not None:
                updates["google_sheet_urls"] = google_sheet_urls
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
                    if google_sheet_urls is not None:
                        updates["google_sheet_urls"] = google_sheet_urls
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
                res = self.in_memory_jobs.get(job_id)
                logging.info(
                    f"JobManager: get_job: job_id={job_id}, found={res is not None}, keys={list(self.in_memory_jobs.keys())}, id(in_memory_jobs)={id(self.in_memory_jobs)}"
                )
                return res


def msgpack_encode(obj):
    """Custom encoder for msgpack to handle datetimes and other types."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


class MeetManagerService(pb2_grpc.MeetManagerServiceServicer):
    def __init__(self):
        # Initialize storage provider
        self.storage: StorageProvider
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if bucket_name:
            self.storage = GCSStorageProvider(bucket_name)
        else:
            base_storage_dir = os.getenv("STORAGE_BASE_DIR")
            if not base_storage_dir:
                if getattr(sys, "frozen", False):
                    base_storage_dir = os.path.join(getattr(sys, "_MEIPASS", ""), DATA_DIR)
                else:
                    base_storage_dir = os.path.join(os.path.dirname(__file__), DATA_DIR)
            logging.info(f"STORAGE_BASE_DIR resolved to: {base_storage_dir} (frozen={getattr(sys, 'frozen', False)})")
            self.storage = LocalStorageProvider(base_storage_dir)

            # Ensure default Sample_Data.json exists in base_storage_dir
            import shutil

            sample_dest = os.path.join(base_storage_dir, SOURCE_FILE)
            if not os.path.exists(sample_dest):
                sample_src = ""
                if getattr(sys, "frozen", False):
                    sample_src = os.path.join(getattr(sys, "_MEIPASS", ""), "data", SOURCE_FILE)
                else:
                    sample_src = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATA_DIR, SOURCE_FILE)

                if os.path.exists(sample_src):
                    logging.info(f"Copying default {SOURCE_FILE} to storage: {sample_dest}")
                    os.makedirs(os.path.dirname(sample_dest), exist_ok=True)
                    shutil.copy2(sample_src, sample_dest)
                else:
                    logging.warning(f"Default {SOURCE_FILE} source NOT FOUND at {sample_src}")

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
                    logging.debug(f"DEBUG: Failed to load user config for {self._mask_uid(uid)}: {e}")
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
                logging.debug(
                    f"E2E: uid={self._mask_uid(uid)}, file={self._mask_path(user_path)}, exists={storage_exists}"
                )

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
                            logging.debug(f"DEBUG: Returning cached data for {self._mask_uid(uid)}/{filename}")
                            return entry["data"], config
                        else:
                            logging.debug(
                                f"DEBUG: Cache stale for {uid}/{filename} (mtime {mtime} != {entry['mtime']})"
                            )
                    except Exception as e:
                        logging.debug(f"DEBUG: Cache check error for {self._mask_uid(uid)}/{filename}: {e}")
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

            logging.debug(f"DEBUG: Loading data from {self._mask_path(user_path)}...")
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
                        logging.debug(f"DEBUG: Evicted {self._mask_uid(oldest_uid)} from user cache to save memory")

                    logging.debug(
                        f"DEBUG: Data loaded and cached for {self._mask_uid(uid)}/{filename} (mtime: {mtime})"
                    )
                except Exception as e:
                    logging.debug(f"DEBUG: Failed to update cache for {self._mask_uid(uid)}/{filename}: {e}")

                return cache, config
            except Exception as e:
                logging.error(f"DEBUG: Error loading data from {self._mask_path(user_path)}: {e}")
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
        from handlers.dataset_uploader import upload_dataset

        return upload_dataset(request_iterator, context, self, pb2)

    def GetDashboardStats(self, request, context):
        request = request or pb2.GetDashboardStatsRequest()
        cache, _ = self._load_user_data(context)

        teams = self._get_table(cache, "team")
        athletes = self._get_table(cache, "athlete")
        events = self._get_table(cache, "event")
        meets = self._get_table(cache, "meet")

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

    def _format_age(self, low, high):
        if self._safe_int(low) == 0 and self._safe_int(high) == 0:
            return "Open"
        if self._safe_int(low) == 0:
            return f"{high} & Under"
        if self._safe_int(high) == 0:
            return f"{low} & Over"
        return f"{low}-{high}"

    def _get_table(self, cache, name):
        """Helper to retrieve a table from cache with case-insensitive key lookup."""
        if not cache:
            logging.debug(f"DEBUG: _get_table('{name}') -> cache is empty")
            return []

        # Try direct lookup first (most common)
        if name in cache:
            return cache[name]

        # Try lowercase lookup (normalized by MmToJsonConverter)
        lower_name = name.lower()
        if lower_name in cache:
            return cache[lower_name]

        # Try plural/singular variations
        variations = [lower_name, lower_name + "s"]
        if lower_name.endswith("s"):
            variations.append(lower_name[:-1])

        # Exhaustive case-insensitive search
        for actual_key in cache.keys():
            lower_actual = actual_key.lower().strip()
            if lower_actual in variations:
                logging.debug(f"DEBUG: _get_table('{name}') found match via actual_key='{actual_key}'")
                return cache[actual_key]

        logging.warning(f"DEBUG: _get_table('{name}') NOT FOUND. Available keys: {list(cache.keys())}")
        return []

    def _get_field(self, d, keys, default=None):
        """Case-insensitive lookup for a list of potential field keys in a dictionary."""
        if not d:
            return default
        for k in keys:
            if k in d:
                return d[k]
            # Case-insensitive scan
            lower_k = k.lower().strip()
            for actual_key in d.keys():
                if actual_key.lower().strip() == lower_k:
                    return d[actual_key]
        return default

    def _mask_path(self, path: str) -> str:
        """Masks sensitive parts of a path for safe logging."""
        if not path:
            return ""
        normalized_path = path.replace("\\", "/")
        if normalized_path.startswith("users/"):
            parts = normalized_path.split("/")
            if len(parts) > 1:
                uid = parts[1]
                masked_uid = self._mask_uid(uid)
                return "/".join(["users", masked_uid] + parts[2:])
        return path

    def _mask_uid(self, uid: str) -> str:
        """Masks a UID for safe logging."""
        if not uid or len(uid) < 8:
            return "***"
        return f"{uid[:4]}...{uid[-4:]}"

    def GetMeets(self, request, context):
        request = request or pb2.GetMeetsRequest()
        cache, _ = self._load_user_data(context)
        uid = self._check_auth(context)

        data = self._get_table(cache, "meet")

        if not data and cache:
            logging.warning(
                f"GetMeets: No 'meet' table found for {self._mask_uid(uid)}. Available tables: {list(cache.keys())}"
            )

        meets = []
        for item in data:
            name = self._get_field(item, ["meet_name1", "meet_name", "mname", "Meet_name1"]) or "Unknown Meet"
            loc = self._get_field(item, ["location", "meet_location", "Meet_location"])
            start = self._format_date(self._get_field(item, ["start", "start_date", "meet_start", "Meet_start"]))
            end = self._format_date(self._get_field(item, ["end", "end_date", "meet_end", "Meet_end"]))
            course_val = self._get_field(item, ["course", "meet_course", "Meet_course"])

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

        logging.debug(f"DEBUG: GetTeams for user {self._mask_uid(uid)}, found {len(data)} teams")

        # Count athletes per team
        ath_counts: dict[int, int] = {}
        for ath in athletes:
            t_id = self._safe_int(self._get_field(ath, ["team_no", "team", "t_id", "Team_no"]))
            ath_counts[t_id] = ath_counts.get(t_id, 0) + 1

        teams = []
        for item in data:
            t_id = self._safe_int(self._get_field(item, ["team_no", "team", "t_id", "Team_no"]))
            teams.append(
                pb2.Team(
                    id=t_id,
                    name=str(self._get_field(item, ["team_name", "tname", "Team_name"]) or "Unknown"),
                    code=str(self._get_field(item, ["team_abbr", "tabbr", "Team_abbr"]) or ""),
                    lsc=str(self._get_field(item, ["team_lsc", "tlsc"]) or ""),
                    city=str(self._get_field(item, ["team_city", "tcity"]) or ""),
                    state=str(self._get_field(item, ["team_statenew", "tstate"]) or ""),
                    athlete_count=ath_counts.get(t_id, 0),
                    color=self._get_team_color(t_id),
                )
            )
        return pb2.GetTeamsResponse(teams=teams)

    def GetTeam(self, request, context):
        request = request or pb2.GetTeamRequest()
        team_id = request.id
        cache, _ = self._load_user_data(context)
        data = self._get_table(cache, "team")
        athlete_data = self._get_table(cache, "athlete")

        athlete_counts: dict[int, int] = {}
        for a in athlete_data:
            t_no = self._safe_int(self._get_field(a, ["team_no", "Team_no"]))
            if t_no:
                athlete_counts[t_no] = athlete_counts.get(t_no, 0) + 1

        for item in data:
            t_id = self._safe_int(self._get_field(item, ["team_no", "team", "t_id", "Team_no"]))
            if t_id == team_id:
                return pb2.GetTeamResponse(
                    team=pb2.Team(
                        id=t_id,
                        name=str(self._get_field(item, ["team_name", "tname", "Team_name"]) or "Unknown"),
                        code=str(self._get_field(item, ["team_abbr", "tabbr", "Team_abbr"]) or ""),
                        lsc=str(self._get_field(item, ["team_lsc", "tlsc"]) or ""),
                        city=str(self._get_field(item, ["team_city", "tcity"]) or ""),
                        state=str(self._get_field(item, ["team_statenew", "tstate"]) or ""),
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
        data = self._get_table(cache, "athlete")

        # Build teams map for name lookups
        teams_map = {}
        for t in self._get_table(cache, "team"):
            t_no = self._safe_int(self._get_field(t, ["team_no", "Team_no"]))
            t_name = self._get_field(t, ["team_name", "Team_name"])
            if t_no:
                teams_map[t_no] = t_name

        athletes = []
        for item in data:
            t_id = self._safe_int(self._get_field(item, ["team_no", "Team_no"]))
            if request and request.team_id and str(t_id) != request.team_id:
                continue

            dob_raw = self._get_field(item, ["ath_birthdate", "birth_date", "Birth_date"]) or ""
            # dob_raw could be a pandas Timestamp or string
            dob = str(dob_raw).split(" ")[0] if dob_raw else ""

            athletes.append(
                pb2.Athlete(
                    id=self._safe_int(self._get_field(item, ["ath_no", "Ath_no"])),
                    first_name=str(self._get_field(item, ["first_name", "First_name"]) or ""),
                    last_name=str(self._get_field(item, ["last_name", "Last_name"]) or ""),
                    gender=str(self._get_field(item, ["ath_sex", "Ath_sex"]) or ""),
                    age=self._safe_int(self._get_field(item, ["ath_age", "Ath_age"])),
                    team_id=t_id,
                    team_name=str(teams_map.get(t_id, "Unknown") or "Unknown"),
                    school_year=str(self._get_field(item, ["school_yr", "Schl_yr"]) or ""),
                    reg_no=str(self._get_field(item, ["reg_no", "Reg_no"]) or ""),
                    date_of_birth=str(dob or ""),
                )
            )
        return pb2.GetAthletesResponse(athletes=athletes)

    def GetAthlete(self, request, context):
        request = request or pb2.GetAthleteRequest()
        ath_id = request.id
        cache, _ = self._load_user_data(context)
        data = self._get_table(cache, "athlete")
        teams_map = {
            self._safe_int(self._get_field(t, ["team_no", "Team_no"])): self._get_field(t, ["team_name", "Team_name"])
            for t in self._get_table(cache, "team")
        }

        for item in data:
            if self._safe_int(self._get_field(item, ["ath_no", "Ath_no"])) == ath_id:
                t_id = self._safe_int(self._get_field(item, ["team_no", "Team_no"]))
                return pb2.GetAthleteResponse(
                    athlete=pb2.Athlete(
                        id=self._safe_int(self._get_field(item, ["ath_no", "Ath_no"])),
                        first_name=str(self._get_field(item, ["first_name", "First_name"]) or ""),
                        last_name=str(self._get_field(item, ["last_name", "Last_name"]) or ""),
                        gender=str(self._get_field(item, ["ath_sex", "Ath_sex"]) or ""),
                        age=self._safe_int(self._get_field(item, ["ath_age", "Ath_age"])),
                        team_id=t_id,
                        team_name=str(teams_map.get(t_id, "Unknown") or "Unknown"),
                        school_year=str(self._get_field(item, ["school_yr", "Schl_yr"]) or ""),
                        reg_no=str(self._get_field(item, ["reg_no", "Reg_no"]) or ""),
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
            evt_ptr = self._get_field(e, ["event_ptr", "Event_ptr", "event_no", "Event_no"])
            if evt_ptr:
                entry_counts[str(evt_ptr)] = entry_counts.get(str(evt_ptr), 0) + 1

        relays = self._get_table(cache, "relay")
        for r in relays:
            evt_ptr = self._get_field(r, ["event_ptr", "Event_ptr", "event_no", "Event_no"])
            if evt_ptr:
                entry_counts[str(evt_ptr)] = entry_counts.get(str(evt_ptr), 0) + 1

        # Build session mapping from Sessitem (Linking Event_ptr to Session No)
        sess_map = {}
        sessitem_table = self._get_table(cache, "sessitem")
        session_table = self._get_table(cache, "session")

        # ptr_to_no: Sess_ptr -> Sess_no
        ptr_to_no = {
            str(self._get_field(s, ["sess_ptr", "Sess_ptr"])): self._safe_int(
                self._get_field(s, ["sess_no", "Sess_no"], 1)
            )
            for s in session_table
            if self._get_field(s, ["sess_ptr", "Sess_ptr"])
        }

        for si in sessitem_table:
            e_ptr = self._get_field(si, ["event_ptr", "Event_ptr"])
            s_ptr = self._get_field(si, ["sess_ptr", "Sess_ptr"])
            if e_ptr and s_ptr:
                sess_map[str(e_ptr)] = ptr_to_no.get(str(s_ptr), 1)

        for item in data:
            raw_stroke = str(self._get_field(item, ["event_stroke", "Event_stroke"]) or "").upper().strip()
            stroke_desc = stroke_map.get(raw_stroke, raw_stroke)

            is_relay = str(self._get_field(item, ["ind_rel", "Ind_rel"]) or "").upper().strip() == "R"
            if raw_stroke == "E" and is_relay:
                stroke_desc = "Medley Relay"
            elif is_relay and stroke_desc != raw_stroke:
                stroke_desc += " Relay"

            raw_gender = str(self._get_field(item, ["event_sex", "Event_sex"]) or "").upper().strip()
            gender_desc = gender_map.get(raw_gender, raw_gender)

            evt_ptr_val = self._get_field(item, ["event_ptr", "Event_ptr"]) or self._get_field(
                item, ["event_no", "Event_no"]
            )
            evt_ptr_int = self._safe_int(evt_ptr_val)
            evt_no = self._safe_int(self._get_field(item, ["event_no", "Event_no"]))
            dist = self._safe_int(self._get_field(item, ["event_dist", "Event_dist"]))

            low_age = self._safe_int(self._get_field(item, ["low_age", "Low_age"]))
            high_age = self._safe_int(self._get_field(item, ["high_age", "High_age"]))
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

        athletes = {
            self._safe_int(self._get_field(a, ["ath_no", "Ath_no"])): a for a in self._get_table(cache, "athlete")
        }
        teams = {self._safe_int(self._get_field(t, ["team_no", "Team_no"])): t for t in self._get_table(cache, "team")}
        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {
            "B": "Boys",
            "G": "Girls",
            "X": "Mixed",
            "M": "Men",
            "W": "Women",
            "F": "Women",
        }

        for e in self._get_table(cache, "event"):
            e_ptr = self._get_field(e, ["event_ptr", "Event_ptr"]) or self._get_field(e, ["event_no", "Event_no"])
            if e_ptr:
                g = gender_map.get(str(self._get_field(e, ["event_sex", "Event_sex"]) or "").strip(), "")
                d = self._get_field(e, ["event_dist", "Event_dist"]) or ""
                s = stroke_map.get(str(self._get_field(e, ["event_stroke", "Event_stroke"]) or "").strip(), "")
                low = self._safe_int(self._get_field(e, ["low_age", "Low_age"]))
                high = self._safe_int(self._get_field(e, ["high_age", "High_age"]))
                age_group = self._format_age(low, high)
                name = f"{g} {age_group} {d} {s}"
                events_map[self._safe_int(e_ptr)] = name

        result = []
        for idx, item in enumerate(entries_data):
            ath_id = self._safe_int(self._get_field(item, ["ath_no", "Ath_no"]))
            if (
                request
                and request.athlete_id
                and request.athlete_id != "0"
                and self._safe_int(request.athlete_id) != ath_id
            ):
                continue

            athlete = athletes.get(ath_id, {})
            t_id = self._safe_int(self._get_field(athlete, ["team_no", "Team_no"]))
            team_obj = teams.get(t_id, {})

            event_id_val = self._get_field(item, ["event_ptr", "Event_ptr"]) or self._get_field(
                item, ["event_no", "Event_no"]
            )
            event_id_int = self._safe_int(event_id_val)

            # Fix: Only filter if event_id is provided AND is not '0' (default)
            if (
                request
                and request.event_id
                and request.event_id != "0"
                and self._safe_int(request.event_id) != event_id_int
            ):
                continue
            seed = self._get_field(item, ["actualseed_time", "convseed_time", "seed_time", "ConvSeed_time"])

            entry_id_val = self._get_field(item, ["entry_no", "Entry_no"])
            final_id = self._safe_int(entry_id_val) if entry_id_val else idx

            result.append(
                pb2.Entry(
                    id=final_id,
                    athlete_id=ath_id,
                    event_id=event_id_int,
                    team_id=t_id,
                    seed_time=self._format_time(seed),
                    final_time=self._format_time(
                        self._get_field(item, ["fin_time", "pre_time", "Fin_time", "Pre_time"])
                    ),
                    place=self._safe_int(self._get_field(item, ["fin_place", "place", "Fin_place"])),
                    event_name=events_map.get(event_id_int, f"Event {event_id_int}"),
                    athlete_name=f"{self._get_field(athlete, ['first_name', 'First_name']) or ''} {self._get_field(athlete, ['last_name', 'Last_name']) or ''}".strip()
                    or "Unknown Athlete",
                    team_name=str(self._get_field(team_obj, ["team_name", "tname", "Team_name"]) or ""),
                    heat=self._safe_int(self._get_field(item, ["fin_heat", "pre_heat", "Fin_heat", "Pre_heat"])),
                    lane=self._safe_int(self._get_field(item, ["fin_lane", "pre_lane", "Fin_lane", "Pre_lane"])),
                    points=self._safe_float(self._get_field(item, ["ev_score", "Ev_score"])),
                    team_color=self._get_team_color(t_id),
                    status=str(self._get_field(item, ["fin_stat", "pre_stat", "Fin_stat", "Pre_stat"]) or ""),
                )
            )
        return pb2.GetEntriesResponse(entries=result)

    def ListDatasets(self, request, context):
        request = request or pb2.ListDatasetsRequest()
        uid = self._check_auth(context)
        config = self._load_user_config(context)
        active_file = config.get("active_dataset", SOURCE_FILE)

        logging.info(f"ListDatasets: uid={self._mask_uid(uid)}, active_file={active_file}")
        datasets = []
        try:
            # List files from users/[uid]/
            user_prefix = os.path.join("users", uid)
            if hasattr(self.storage, "_get_full_path"):
                logging.info("ListDatasets: Checking local path")

            # Retry loop for eventual consistency in CI environments            files = []
            for attempt in range(5):
                files = self.storage.list_files(user_prefix)
                if files:
                    break
                if attempt < 4:
                    logging.info(f"ListDatasets: No files found for {self._mask_uid(uid)}, retrying in 2s...")
                    time.sleep(2)

            logging.info(f"ListDatasets: Found {len(files)} files in {self._mask_path(user_prefix)}: {files}")

            # Also include default Sample_Data.json if it exists and user has no files?
            # For simplicity, let's just list user's files

            for rel_path in files:
                # ONLY allow files in the root user directory (not subdirs like 'published/' or 'bundles/')
                # rel_path looks like "users/UID/filename.ext" or "users/UID/published/file.json"
                normalized_path = rel_path.replace("\\", "/")
                parts = normalized_path.split("/")
                if len(parts) != 3:
                    continue

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
        exists = self.storage.exists(user_path)
        logging.info(
            f"SetActiveDataset: uid={self._mask_uid(uid)}, filename={filename}, user_path={self._mask_path(user_path)}, exists={exists}"
        )

        if not exists and not (filename == SOURCE_FILE and self.storage.exists(SOURCE_FILE)):
            logging.warning(f"SetActiveDataset: File {filename} NOT FOUND in user directory for {self._mask_uid(uid)}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"File {filename} not found.")
            return pb2.SetActiveDatasetResponse()

        with self._lock:
            logging.info(f"Switching user {self._mask_uid(uid)} dataset to {filename}...")
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
            logging.debug(f"SetActiveDataset: Forcing synchronous extraction for {self._mask_uid(uid)}/{filename}...")
            try:
                self._load_user_data(context)
                # Clear cache AGAIN after extraction if it's an E2E-like environment
                # to ensure subsequent calls also bypass any race-condition cache entries.
                metadata = dict(context.invocation_metadata() if context else [])
                if os.getenv("IS_E2E") == "true" or "x-e2e-uid" in metadata or "x-user-id" in metadata:
                    if uid in self._user_cache:
                        del self._user_cache[uid]
                logging.debug(f"SetActiveDataset: Extraction complete for {self._mask_uid(uid)}/{filename}")
            except Exception as e:
                logging.error(f"SetActiveDataset: Extraction failed for {self._mask_uid(uid)}/{filename}: {e}")
                # Reset config if extraction failed to prevent a broken active dataset
                config["active_dataset"] = SOURCE_FILE
                self._save_user_config(context, config)
                context.abort(grpc.StatusCode.INTERNAL, f"Dataset extraction failed: {str(e)}")

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
        relays_data = self._get_table(cache, "relay")

        relay_names_data = self._get_table(cache, "relaynames")
        relay_legs_map: dict[tuple[Any, Any, Any], list[Any]] = {}
        for rn in relay_names_data:
            key = (
                self._get_field(rn, ["event_ptr", "Event_ptr"]),
                self._safe_int(self._get_field(rn, ["team_no", "Team_no"])),
                self._safe_int(self._get_field(rn, ["relay_no", "Relay_no"])),
            )
            if key not in relay_legs_map:
                relay_legs_map[key] = []
            relay_legs_map[key].append(rn)

        teams = {
            self._safe_int(self._get_field(t, ["team_no", "Team_no"])): self._get_field(t, ["team_name", "Team_name"])
            for t in self._get_table(cache, "team")
        }
        athletes = {
            self._safe_int(self._get_field(a, ["ath_no", "Ath_no"])): a for a in self._get_table(cache, "athlete")
        }

        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {
            "B": "Boys",
            "G": "Girls",
            "X": "Mixed",
            "M": "Men",
            "W": "Women",
            "F": "Women",
        }

        for e in self._get_table(cache, "event"):
            e_no = self._get_field(e, ["event_no", "Event_no"]) or self._get_field(e, ["event_ptr", "Event_ptr"])
            if e_no:
                g = gender_map.get(
                    str(self._get_field(e, ["event_sex", "Event_sex"]) or "").strip(),
                    str(self._get_field(e, ["event_sex", "Event_sex"]) or ""),
                )
                d = self._get_field(e, ["event_dist", "Event_dist"]) or ""
                s = stroke_map.get(
                    str(self._get_field(e, ["event_stroke", "Event_stroke"]) or "").strip(),
                    str(self._get_field(e, ["event_stroke", "Event_stroke"]) or ""),
                )
                age_group = self._format_age(
                    self._get_field(e, ["low_age", "Low_age"]),
                    self._get_field(e, ["high_age", "High_age"]),
                )
                name = f"{g} {age_group} {d} {s}"
                events_map[e_no] = name

        result = []
        for idx, item in enumerate(relays_data):
            event_ptr = self._get_field(item, ["event_ptr", "Event_ptr"])
            # Fix: Only filter if event_id is provided AND is not '0' (default)
            if (
                request
                and request.event_id
                and request.event_id != "0"
                and self._safe_int(request.event_id) != self._safe_int(event_ptr)
            ):
                continue

            t_id = self._safe_int(self._get_field(item, ["team_ptr", "team_no", "Team_ptr", "Team_no"]) or 0)
            relay_no = self._safe_int(self._get_field(item, ["relay_no", "Relay_no"]))

            legs = relay_legs_map.get((event_ptr, t_id, relay_no), [])
            legs.sort(key=lambda x: self._safe_int(self._get_field(x, ["pos_no", "Pos_no"]), 99))

            leg_names = ["", "", "", ""]
            for leg in legs:
                try:
                    pos = self._safe_int(self._get_field(leg, ["pos_no", "Pos_no"], 0))
                    if 1 <= pos <= 4:
                        ath_id = self._safe_int(self._get_field(leg, ["ath_no", "Ath_no"]))
                        ath = athletes.get(ath_id)
                        if ath:
                            leg_names[pos - 1] = (
                                f"{self._get_field(ath, ['first_name', 'First_name']) or ''} {self._get_field(ath, ['last_name', 'Last_name']) or ''}"
                            )
                except (ValueError, TypeError):
                    continue

            seed = (
                self._get_field(item, ["actualseed_time", "actual_seed"])
                or self._get_field(item, ["convseed_time", "conv_seed"])
                or self._get_field(item, ["seed_time", "Seed_time"])
            )

            result.append(
                pb2.Relay(
                    id=idx,
                    event_id=self._safe_int(self._get_field(item, ["event_ptr", "Event_ptr"])),
                    team_id=self._safe_int(t_id),
                    team_name=str(teams.get(t_id, "Unknown") or "Unknown"),
                    leg1_name=str(leg_names[0] or ""),
                    leg2_name=str(leg_names[1] or ""),
                    leg3_name=str(leg_names[2] or ""),
                    leg4_name=str(leg_names[3] or ""),
                    seed_time=self._format_time(seed),
                    final_time=self._format_time(self._get_field(item, ["fin_time", "Fin_time"])),
                    place=self._safe_int(self._get_field(item, ["fin_place", "place", "Fin_place"])),
                    event_name=str(events_map.get(self._safe_int(event_ptr), f"Event {event_ptr}") or ""),
                    relay_letter=str(self._get_field(item, ["team_ltr", "Team_ltr"]) or ""),
                    heat=self._safe_int(self._get_field(item, ["fin_heat", "Fin_heat"])),
                    lane=self._safe_int(self._get_field(item, ["fin_lane", "Fin_lane"])),
                    team_color=self._get_team_color(t_id),
                    status=str(self._get_field(item, ["fin_stat", "pre_stat", "Fin_stat", "Pre_stat"]) or ""),
                )
            )
        return pb2.GetRelaysResponse(relays=result)

    def GetScores(self, request, context):
        request = request or pb2.GetScoresRequest()
        cache, config = self._load_user_data(context)

        teams_data = self._get_table(cache, "team")
        teams = {
            self._safe_int(self._get_field(t, ["team_no", "Team_no"])): {
                "name": str(self._get_field(t, ["team_name", "tname", "Team_name"]) or "Unknown"),
                "id": self._safe_int(self._get_field(t, ["team_no", "Team_no"])),
            }
            for t in teams_data
        }
        scores = {t_id: {"ind": 0.0, "rel": 0.0} for t_id in teams}

        entries_data = self._get_table(cache, "entry")
        athletes = {
            self._safe_int(self._get_field(a, ["ath_no", "Ath_no"])): a for a in self._get_table(cache, "athlete")
        }
        events_sex_map = {
            str(
                self._get_field(e, ["event_no", "Event_no"]) or self._get_field(e, ["event_ptr", "Event_ptr"]) or ""
            ): str(self._get_field(e, ["event_sex", "Event_sex"]) or "M").strip()
            for e in self._get_table(cache, "event")
        }

        if entries_data:
            for e in entries_data:
                ath_id = self._safe_int(self._get_field(e, ["ath_no", "Ath_no"]))
                ath = athletes.get(ath_id)
                if ath:
                    t_id = self._safe_int(self._get_field(ath, ["team_no", "Team_no"]))
                    if t_id in scores:
                        e_id = str(self._get_field(e, ["event_ptr", "Event_ptr"]) or "")
                        sex = events_sex_map.get(e_id, str(self._get_field(ath, ["ath_sex", "Ath_sex"]) or "M"))
                        val = self._calculate_points(e, sex, False, cache)
                        scores[t_id]["ind"] += val

        relays_data = self._get_table(cache, "relay")
        if relays_data:
            for r in relays_data:
                t_id = self._safe_int(self._get_field(r, ["team_no", "Team_no"]))
                if not t_id or t_id == 0:
                    t_id = self._safe_int(self._get_field(r, ["team_ptr", "Team_ptr"]))

                if t_id in scores:
                    e_id = str(self._get_field(r, ["event_ptr", "Event_ptr"]) or "")
                    sex = events_sex_map.get(e_id, str(self._get_field(r, ["rel_sex", "Rel_sex"]) or "X"))
                    val = self._calculate_points(r, sex, True, cache)
                    scores[t_id]["rel"] += val

        meets = self._get_table(cache, "meet")
        meet_name = config.get("meet_name")
        if not meet_name and meets:
            m = meets[0]
            meet_name = self._get_field(m, ["meet_name1", "meet_name", "mname", "Meet_name1"])

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

    def _calculate_points(self, item, sex, is_relay, cache):
        score = self._safe_float(self._get_field(item, ["ev_score", "Ev_score"], 0))
        if score > 0:
            return score

        place = self._safe_int(self._get_field(item, ["fin_place", "place", "Fin_place"], 0))
        if place <= 0:
            return 0.0

        div = str(self._get_field(item, ["div_no", "Div_no", "score_divno"], "0"))
        sex_map = {"B": "M", "M": "M", "G": "F", "W": "F", "F": "F", "X": "M"}
        mapped_sex = sex_map.get(sex.upper(), "M")

        scoring_map = self._get_scoring_map(cache)
        div_map = scoring_map.get(div, scoring_map.get("0", {}))
        sex_scores = div_map.get(mapped_sex, div_map.get("M", {}))

        score_data = sex_scores.get(place, {})
        return score_data.get("rel" if is_relay else "ind", 0.0)

    def _get_scoring_map(self, cache):
        scoring_data = self._get_table(cache, "scoring")
        scoring_map: dict[str, dict[str, dict[int, dict[str, float]]]] = {}
        for row in scoring_data:
            div = str(self._get_field(row, ["score_divno", "div_no"], "0"))
            sex = str(self._get_field(row, ["score_sex", "sex"], "M")).upper()
            place = self._safe_int(self._get_field(row, ["score_place", "place"], 0))

            if div not in scoring_map:
                scoring_map[div] = {}
            if sex not in scoring_map[div]:
                scoring_map[div][sex] = {}

            scoring_map[div][sex][place] = {
                "ind": self._safe_float(self._get_field(row, ["ind_score", "Ind_score"], 0)),
                "rel": self._safe_float(self._get_field(row, ["rel_score", "Rel_score"], 0)),
            }
        return scoring_map

    def GetEventScores(self, request, context):
        request = request or pb2.GetEventScoresRequest()
        cache, _ = self._load_user_data(context)
        entries = self._get_table(cache, "entry")
        relays = self._get_table(cache, "relay")
        athletes_map = {
            self._safe_int(self._get_field(a, ["ath_no", "Ath_no"])): a for a in self._get_table(cache, "athlete")
        }
        teams_map = {
            self._safe_int(self._get_field(t, ["team_no", "Team_no"])): self._get_field(t, ["team_name", "Team_name"])
            for t in self._get_table(cache, "team")
        }

        events_map = {}
        stroke_map = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}
        gender_map = {
            "B": "Boys",
            "G": "Girls",
            "X": "Mixed",
            "M": "Men",
            "W": "Women",
            "F": "Women",
        }

        event_dict: dict[str, dict[str, Any]] = {}
        event_raw_map = {}

        for e in self._get_table(cache, "event"):
            e_no = self._get_field(e, ["event_no", "Event_no"]) or self._get_field(e, ["event_ptr", "Event_ptr"])
            if not e_no:
                continue

            event_raw_map[str(e_no)] = e
            g = gender_map.get(str(self._get_field(e, ["event_sex", "Event_sex"]) or "").strip(), "")
            d = self._get_field(e, ["event_dist", "Event_dist"]) or ""
            s_raw = str(self._get_field(e, ["event_stroke", "Event_stroke"]) or "").strip()
            s = stroke_map.get(s_raw, s_raw)

            is_relay = str(self._get_field(e, ["ind_rel", "Ind_rel"]) or "").upper().strip() == "R"
            if s_raw == "E" and is_relay:
                s = "Medley Relay"
            elif is_relay and s != s_raw:
                s += " Relay"

            low = self._get_field(e, ["low_age", "Low_age"])
            high = self._get_field(e, ["high_age", "High_age"])
            age_group = self._format_age(low, high)
            name = f"{g} {age_group} {d} {s}"
            events_map[str(e_no)] = name
            event_dict[str(e_no)] = {"id": self._safe_int(e_no), "name": name, "entries": []}

        for item in entries:
            e_id = str(self._get_field(item, ["event_ptr", "Event_ptr"]) or "")
            if e_id not in event_dict:
                continue

            ath_id = self._safe_int(self._get_field(item, ["ath_no", "Ath_no"]))
            ath = athletes_map.get(ath_id)
            t_id = self._safe_int(self._get_field(ath, ["team_no", "Team_no"])) if ath else 0
            place = self._safe_int(self._get_field(item, ["fin_place", "place", "Fin_place"]))

            ev_raw = event_raw_map.get(e_id, {})
            points = self._calculate_points(
                item, str(self._get_field(ev_raw, ["event_sex", "Event_sex"]) or "M"), False, cache
            )

            if not self._get_field(item, ["fin_time", "Fin_time"]) and place <= 0:
                continue

            seed = self._get_field(item, ["actualseed_time", "convseed_time", "seed_time"])

            entry_obj = pb2.Entry(
                id=0,
                event_id=self._safe_int(e_id),
                athlete_id=ath_id,
                athlete_name=f"{self._get_field(ath, ['first_name', 'First_name']) or ''} {self._get_field(ath, ['last_name', 'Last_name']) or ''}"
                if ath
                else "Unknown",
                team_id=t_id,
                team_name=str(teams_map.get(t_id, "Unknown")),
                seed_time=self._format_time(seed),
                final_time=self._format_time(self._get_field(item, ["fin_time", "Fin_time"])),
                place=place,
                points=points,
                event_name=events_map.get(e_id, ""),
            )
            event_dict[e_id]["entries"].append(entry_obj)

        for item in relays:
            e_id = str(self._get_field(item, ["event_ptr", "Event_ptr"]) or "")
            if e_id not in event_dict:
                continue

            t_id = self._safe_int(self._get_field(item, ["team_ptr", "team_no", "Team_ptr", "Team_no"]))
            place = self._safe_int(self._get_field(item, ["fin_place", "place", "Fin_place"]))
            rel_ltr = self._get_field(item, ["team_ltr", "Team_ltr"]) or ""

            ev_raw = event_raw_map.get(e_id, {})
            points = self._calculate_points(
                item, str(self._get_field(ev_raw, ["event_sex", "Event_sex"]) or "X"), True, cache
            )

            if not self._get_field(item, ["fin_time", "Fin_time"]) and place <= 0:
                continue

            seed = (
                self._get_field(item, ["actualseed_time", "actual_seed"])
                or self._get_field(item, ["convseed_time", "conv_seed"])
                or self._get_field(item, ["seed_time", "Seed_time"])
            )

            entry_obj = pb2.Entry(
                id=0,
                event_id=self._safe_int(e_id),
                athlete_id=0,
                athlete_name=f"Relay Team ({rel_ltr})" if rel_ltr else "Relay Team",
                team_id=t_id,
                team_name=teams_map.get(t_id, "Unknown"),
                seed_time=self._format_time(seed),
                final_time=self._format_time(self._get_field(item, ["fin_time", "Fin_time"])),
                place=place,
                points=points,
                heat=self._safe_int(self._get_field(item, ["fin_heat", "Fin_heat"], 0)),
                lane=self._safe_int(self._get_field(item, ["fin_lane", "Fin_lane"], 0)),
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
        from handlers.report_handler import generate_report

        return generate_report(request, context, self, pb2)

    def GenerateReportBundle(self, request, context):
        from handlers.report_handler import generate_report_bundle

        return generate_report_bundle(request, context, self, pb2)

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
        gs_urls = job.get("google_sheet_urls") or []

        return pb2.GetJobStatusResponse(
            status=job["status"],
            progress=job["progress"],
            message=job["message"],
            bundle_url=b_url,
            google_sheet_urls=gs_urls,
        )

    def GetSessions(self, request, context):
        request = request or pb2.GetSessionsRequest()
        cache, _ = self._load_user_data(context)
        data = self._get_table(cache, "session")
        meets = self._get_table(cache, "meet")

        meet_start = None
        if meets:
            m = meets[0]
            date_str = self._get_field(m, ["start", "start_date", "Start", "Start_date"]) or ""
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
            s_ptr = self._get_field(si, ["sess_ptr", "Sess_ptr"])
            if s_ptr:
                event_counts_map[str(s_ptr)] = event_counts_map.get(str(s_ptr), 0) + 1

        for e in event_table:
            s_no = self._safe_int(self._get_field(e, ["sess_no", "Sess_no"])) or 1
            if s_no:
                sess_no_counts[s_no] = sess_no_counts.get(s_no, 0) + 1

        sessions_to_process = []
        if data:
            for item in data:
                s_ptr = self._get_field(item, ["sess_ptr", "Sess_ptr"])
                s_no = self._safe_int(self._get_field(item, ["sess_no", "Sess_no"]))
                e_cnt = self._safe_int(self._get_field(item, ["event_cnt", "Event_cnt"]))

                if not e_cnt:
                    if s_ptr:
                        e_cnt = event_counts_map.get(str(s_ptr), 0)
                    if not e_cnt and s_no:
                        e_cnt = sess_no_counts.get(s_no, 0)

                sessions_to_process.append(
                    {
                        "id": str(s_no or "0"),
                        "name": str(self._get_field(item, ["sess_name", "sname", "Sess_name"]) or f"Session {s_no}"),
                        "day": self._safe_int(self._get_field(item, ["sess_day", "day", "Sess_day"]) or 1),
                        "warmup": self._safe_int(self._get_field(item, ["sess_warmup", "Sess_warmup"]) or 0),
                        "starttime": self._safe_int(self._get_field(item, ["sess_starttime", "Sess_starttime"]) or 0),
                        "event_cnt": e_cnt,
                        "source_item": item,
                    }
                )
        else:
            sess_ids = sorted({self._safe_int(self._get_field(e, ["sess_no", "Sess_no"]) or 1) for e in event_table})
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
        from handlers.publish_handler import publish_meet_data

        return publish_meet_data(request, context, self, pb2)

    def SyncDQs(self, request, context):
        from handlers.dq_handler import sync_dqs

        return sync_dqs(request, context, self, pb2)

    def GetFile(self, request, context):
        # Allow unauthenticated access specifically for sample-user paths (public sample data)
        is_sample = request.path.startswith("users/sample-user/")

        if not is_sample:
            # System-level bypass for stateless access
            token = _get_data_access_token()
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

    def ValidateMeet(self, request, context):
        """Validate the active dataset for registry anomalies and rules violations."""
        try:
            cache, _ = self._load_user_data(context)
            findings = validate_meet_data(cache)

            # Retrieve size metrics safely for the success message
            athletes = self._get_table(cache, "athlete")
            events = self._get_table(cache, "event")
            entries = self._get_table(cache, "entry")

            return pb2.ValidateMeetResponse(
                success=True,
                message=f"Validation completed. Analyzed {len(athletes)} swimmers, {len(events)} events, and {len(entries)} entries.",
                findings=findings,
            )
        except Exception as e:
            logging.error(f"ValidateMeet failed: {e}")
            return pb2.ValidateMeetResponse(success=False, message=f"Validation check failed: {str(e)}")

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


ACTUAL_REST_PORT = 0


def write_active_ports(grpc_port: int, rest_port: int):
    try:
        dir_path = os.path.expanduser("~/.mmtools")
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, "active_ports.json")
        data = {
            "grpc_port": grpc_port,
            "rest_port": rest_port,
            "pid": os.getpid(),
            "timestamp": int(time.time()),
        }
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        logging.info(f"Wrote active ports to local registry: {file_path}")
    except Exception as e:
        logging.warning(f"Failed to write active ports to registry: {e}")


def serve_health_check():
    import base64

    from google.protobuf import json_format

    class MockContext:
        def __init__(self, metadata_headers_or_user_id):
            if isinstance(metadata_headers_or_user_id, str):
                user_id = metadata_headers_or_user_id
            else:
                user_id = metadata_headers_or_user_id.get("x-user-id", "dev-user")
            self._metadata = [("x-user-id", user_id)]

        def invocation_metadata(self):
            return self._metadata

        def set_code(self, code):
            pass

        def set_details(self, details):
            pass

        def abort(self, code, details):
            raise Exception(f"gRPC Abort: {code} - {details}")

    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def _send_cors_headers(self):
            origin = self.headers.get("Origin")
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Credentials", "true")
            else:
                self.send_header("Access-Control-Allow-Origin", "*")

        def do_OPTIONS(self):
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, x-user-id, authorization")
            self.end_headers()

        def do_GET(self):
            import urllib.parse

            parsed_url = urllib.parse.urlparse(self.path)

            if parsed_url.path == "/health":
                self.send_response(200)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(b"OK")
            elif parsed_url.path == "/api/data":
                params = urllib.parse.parse_qs(parsed_url.query)
                token = params.get("token", [""])[0]
                relative_path = params.get("path", [""])[0]

                # Check data access token if configured
                configured_token = _get_data_access_token()
                if configured_token and token != configured_token:
                    self.send_response(403)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(b"Unauthorized access")
                    return

                if not relative_path:
                    self.send_response(400)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(b"Missing path parameter")
                    return

                try:
                    # Resolve safe full path
                    base_storage_dir = os.getenv("STORAGE_BASE_DIR")
                    if not base_storage_dir:
                        if getattr(sys, "frozen", False):
                            base_storage_dir = os.path.join(getattr(sys, "_MEIPASS", ""), DATA_DIR)
                        else:
                            base_storage_dir = os.path.join(os.path.dirname(__file__), DATA_DIR)
                    base_abs = os.path.abspath(base_storage_dir)
                    full_path = os.path.abspath(os.path.join(base_abs, relative_path))

                    logging.info(
                        f"do_GET /api/data: path={relative_path} resolved base_abs={base_abs} full_path={full_path} exists={os.path.exists(full_path)}"
                    )

                    # Use normcase to handle case-insensitive and slash-agnostic comparison on Windows
                    base_abs_norm = os.path.normcase(base_abs)
                    full_path_norm = os.path.normcase(full_path)

                    if not full_path_norm.startswith(base_abs_norm):
                        self.send_response(403)
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(b"Access Denied")
                        return

                    if not os.path.exists(full_path) or not os.path.isfile(full_path):
                        self.send_response(404)
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(b"File Not Found")
                        return

                    # Determine Content-Type
                    content_type = "application/octet-stream"
                    if full_path.endswith(".zip"):
                        content_type = "application/zip"
                    elif full_path.endswith(".pdf"):
                        content_type = "application/pdf"
                    elif full_path.endswith(".html"):
                        content_type = "text/html"

                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self._send_cors_headers()
                    self.send_header("Access-Control-Allow-Headers", "*")
                    self.end_headers()

                    with open(full_path, "rb") as f:
                        self.wfile.write(f.read())

                except Exception as e:
                    self.send_response(500)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(str(e).encode("utf-8"))
            else:
                self.send_response(404)
                self._send_cors_headers()
                self.end_headers()

        def do_POST(self):
            import json

            if self.path.startswith("/api/sync-dqs") or self.path.startswith("/api/submit-dq"):
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")

                # Parse query parameters safely
                import urllib.parse

                parsed_url = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed_url.query)

                token = params.get("token", [""])[0]
                uid = params.get("uid", ["dev-user"])[0]

                # Check data access token if configured
                configured_token = _get_data_access_token()
                if configured_token and token != configured_token:
                    self.send_response(403)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(b"Unauthorized access")
                    return

                import json

                try:
                    payload = json.loads(body)
                    if self.path.startswith("/api/submit-dq"):
                        dqs_list = [payload]
                    else:
                        dqs_list = payload if isinstance(payload, list) else [payload]

                    servicer = MeetManagerService()
                    context = MockContext(uid)

                    resp = servicer.SyncDQs(
                        pb2.SyncDQsRequest(dqs_json=json.dumps(dqs_list), uid=uid, access_token=configured_token),
                        context,
                    )

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.send_header("Access-Control-Allow-Headers", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": resp.success, "message": resp.message}).encode("utf-8"))
                except Exception as e:
                    self.send_response(500)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(str(e).encode("utf-8"))
            elif self.path.startswith("/api/grpc/"):
                method_name = self.path[len("/api/grpc/") :]

                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")

                try:
                    servicer = MeetManagerService()

                    if method_name in ["GetDisqualifications", "DeleteDq", "ClearAllDqs"]:
                        uid = self.headers.get("x-user-id") or "desktop-user"
                        if method_name == "GetDisqualifications":
                            filename = "synced_dqs.json"
                            user_path = f"users/{uid}/{filename}"
                            dqs = []
                            if servicer.storage.exists(user_path):
                                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                                    tmp_path = tmp.name
                                try:
                                    servicer.storage.download_file(user_path, tmp_path)
                                    with open(tmp_path, encoding="utf-8") as f:
                                        dqs = json.load(f)
                                except Exception as e:
                                    logging.error(f"Error reading synced_dqs.json: {e}")
                                finally:
                                    if os.path.exists(tmp_path):
                                        os.remove(tmp_path)

                            formatted_dqs = []
                            for dq in dqs:
                                formatted_dqs.append(
                                    {
                                        "id": dq.get("clientDqId") or dq.get("id") or "",
                                        "event": dq.get("event") or dq.get("event_id") or "",
                                        "heat": dq.get("heat") or 0,
                                        "lane": dq.get("lane") or 0,
                                        "swimmer": dq.get("swimmer") or "",
                                        "client_id": dq.get("client_id") or "",
                                        "infraction_code": dq.get("infraction_code") or dq.get("dq_code") or "",
                                        "notes": dq.get("notes") or "",
                                        "ingested": dq.get("ingested") or True,
                                        "createdAt": dq.get("createdAt") or dq.get("timestamp") or "",
                                    }
                                )
                            resp_json = json.dumps({"disqualifications": formatted_dqs})
                        elif method_name == "DeleteDq":
                            data = json.loads(body) if body else {}
                            dq_id = data.get("dqId")
                            filename = "synced_dqs.json"
                            user_path = f"users/{uid}/{filename}"
                            dqs = []
                            if servicer.storage.exists(user_path):
                                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                                    tmp_path = tmp.name
                                try:
                                    servicer.storage.download_file(user_path, tmp_path)
                                    with open(tmp_path, encoding="utf-8") as f:
                                        dqs = json.load(f)
                                except Exception as e:
                                    logging.error(f"Error reading synced_dqs.json: {e}")
                                finally:
                                    if os.path.exists(tmp_path):
                                        os.remove(tmp_path)

                            updated_dqs = [dq for dq in dqs if (dq.get("clientDqId") or dq.get("id")) != dq_id]

                            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp_w:
                                json.dump(updated_dqs, tmp_w, indent=2)
                                tmp_path = tmp_w.name
                            try:
                                servicer.storage.upload_file(tmp_path, user_path)
                            finally:
                                if os.path.exists(tmp_path):
                                    os.remove(tmp_path)

                            if uid in servicer._user_cache:
                                del servicer._user_cache[uid]
                            resp_json = json.dumps({"success": True, "message": "DQ deleted"})
                        else:  # ClearAllDqs
                            filename = "synced_dqs.json"
                            user_path = f"users/{uid}/{filename}"
                            if servicer.storage.exists(user_path):
                                servicer.storage.delete_file(user_path)
                            if uid in servicer._user_cache:
                                del servicer._user_cache[uid]
                            resp_json = json.dumps({"success": True, "message": "DQs cleared"})

                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self._send_cors_headers()
                        self.send_header("Access-Control-Allow-Headers", "*")
                        self.end_headers()
                        self.wfile.write(resp_json.encode("utf-8"))
                        return
                    else:
                        method = getattr(servicer, method_name, None)
                        if not method:
                            self.send_response(404)
                            self._send_cors_headers()
                            self.end_headers()
                            return

                        context = MockContext(self.headers)

                    if method_name == "UploadDataset":
                        import json

                        data = json.loads(body)
                        filename = data["filename"]
                        content_str = data["content"]
                        if "," in content_str:
                            content_str = content_str.split(",", 1)[1]
                        content = base64.b64decode(content_str)

                        def request_generator():
                            yield pb2.UploadDatasetRequest(filename=filename)
                            yield pb2.UploadDatasetRequest(chunk=content)

                        resp = servicer.UploadDataset(request_generator(), context)
                        resp_dict = json_format.MessageToDict(
                            resp, preserving_proto_field_name=True, use_integers_for_enums=True
                        )
                        resp_json = json.dumps(resp_dict)
                    else:
                        request_class = getattr(pb2, f"{method_name}Request", None)
                        if not request_class:
                            self.send_response(500)
                            self._send_cors_headers()
                            self.end_headers()
                            self.wfile.write(f"Request class not found: {method_name}Request".encode())
                            return

                        import json

                        json_data = json.loads(body) if body else {}
                        req = json_format.ParseDict(json_data, request_class())

                        resp = method(req, context)
                        resp_dict = json_format.MessageToDict(
                            resp, preserving_proto_field_name=True, use_integers_for_enums=True
                        )
                        resp_json = json.dumps(resp_dict)

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.send_header("Access-Control-Allow-Headers", "*")
                    self.end_headers()
                    self.wfile.write(resp_json.encode("utf-8"))
                except Exception as e:
                    self.send_response(500)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(str(e).encode("utf-8"))
            else:
                self.send_response(404)
                self._send_cors_headers()
                self.end_headers()

        def log_message(self, format, *args):
            return

    import socket
    import socketserver

    class ThreadingHTTPServerV6(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        address_family = socket.AF_INET6

    class ThreadingHTTPServerV4(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        address_family = socket.AF_INET

    in_docker = os.path.exists("/.dockerenv")
    is_local = (os.getenv("GRPC_AUTH_DISABLED") == "true" or not os.getenv("K_SERVICE")) and not in_docker
    bind_v6 = "::1" if is_local else "::"
    bind_v4 = "127.0.0.1" if is_local else "0.0.0.0"

    rest_port = int(os.getenv("REST_PORT", "8081"))
    httpd: Any = None
    for port_attempt in range(rest_port, rest_port + 10):
        try:
            # Attempt dual-stack IPv6/IPv4 binding first
            try:
                httpd = ThreadingHTTPServerV6((bind_v6, port_attempt), HealthHandler)
                try:
                    # Enable dual-stack explicitly (V6ONLY=0)
                    httpd.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                except Exception:
                    pass
            except Exception:
                # Fallback to IPv4
                httpd = ThreadingHTTPServerV4((bind_v4, port_attempt), HealthHandler)
            rest_port = port_attempt
            global ACTUAL_REST_PORT
            ACTUAL_REST_PORT = rest_port
            break
        except Exception:
            logging.warning(f"Port {port_attempt} already in use, trying next...")

    if httpd is None:
        logging.error("Failed to start REST Gateway server: no free ports found.")
    else:
        logging.info(f"REST Gateway + Health check server starting on port {rest_port}...")
        try:
            httpd.serve_forever()
        except Exception as e:
            logging.error(f"Error in REST Gateway server loop: {e}")


def serve():
    port = os.getenv("PORT", "8080")

    # Configure authentication interceptor
    if os.getenv("GRPC_AUTH_DISABLED") == "true":

        class MockAuthInterceptor(grpc.ServerInterceptor):
            def intercept_service(self, continuation, handler_call_details):
                metadata = {k.lower(): v for k, v in handler_call_details.invocation_metadata}
                uid = metadata.get("x-user-id") or metadata.get("x-e2e-uid") or "dev-user"
                handler = continuation(handler_call_details)
                if handler is None:
                    return None

                # Inline implementation of AuthHandlerWrapper to avoid importing auth_interceptor
                class LocalAuthHandlerWrapper(grpc.RpcMethodHandler):
                    def __init__(self, h, u):
                        self.request_streaming = h.request_streaming
                        self.response_streaming = h.response_streaming
                        self.request_deserializer = h.request_deserializer
                        self.response_serializer = h.response_serializer
                        if self.request_streaming:
                            if self.response_streaming:
                                self.stream_stream = self._wrap(h.stream_stream)
                            else:
                                self.stream_unary = self._wrap(h.stream_unary)
                        else:
                            if self.response_streaming:
                                self.unary_stream = self._wrap(h.unary_stream)
                            else:
                                self.unary_unary = self._wrap(h.unary_unary)
                        self.uid = u

                    def _wrap(self, behavior):
                        def wrapped(request, context):
                            context.uid = self.uid
                            return behavior(request, context)

                        return wrapped

                return LocalAuthHandlerWrapper(handler, uid)

        interceptors = [MockAuthInterceptor()]
        logging.info("gRPC Auth is disabled. Running with local mock auth interceptor.")
    else:
        from auth_interceptor import FirebaseAuthInterceptor

        interceptors = [FirebaseAuthInterceptor()]
        logging.info("gRPC Auth is enabled. Running with FirebaseAuthInterceptor.")

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=interceptors,
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )

    # Graceful shutdown handler
    def handle_sigterm(signum, frame):
        logging.info("SIGTERM/SIGINT received, shutting down...")
        server.stop(5)
        os._exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    # Start health check server in background thread
    health_thread = threading.Thread(target=serve_health_check, daemon=True)
    health_thread.start()

    # Add Health Servicer
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    pb2_grpc.add_MeetManagerServiceServicer_to_server(MeetManagerService(), server)

    # Bind host: loopback for local/desktop, wildcard for cloud and docker container networks
    in_docker = os.path.exists("/.dockerenv")
    bind_address = (
        "127.0.0.1"
        if (os.getenv("GRPC_AUTH_DISABLED") == "true" or not os.getenv("K_SERVICE")) and not in_docker
        else "0.0.0.0"
    )
    grpc_port = int(port)
    actual_port = 0
    for port_attempt in range(grpc_port, grpc_port + 10):
        try:
            res = server.add_insecure_port(f"{bind_address}:{port_attempt}")
            if res > 0:
                actual_port = res
                break
        except Exception:
            logging.warning(f"gRPC Port {port_attempt} already in use, trying next...")

    if actual_port == 0:
        logging.error("Failed to start gRPC server: no free ports found.")
        sys.exit(1)

    logging.info(f"Server starting on {bind_address}:{actual_port}...")
    server.start()

    # Wait briefly for ACTUAL_REST_PORT to be set by the health check thread
    for _ in range(20):
        if ACTUAL_REST_PORT > 0:
            break
        time.sleep(0.1)

    write_active_ports(actual_port, ACTUAL_REST_PORT)
    server.wait_for_termination()


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()

    import os
    import sys

    # Apply macOS Homebrew library resolution fallback under SIP
    if sys.platform == "darwin":
        homebrew_lib = "/opt/homebrew/lib"
        if os.path.exists(homebrew_lib):
            import ctypes.util

            if ctypes.util.find_library.__name__ != "new_find_library":
                orig_find_library = ctypes.util.find_library

                def new_find_library(name):
                    res = orig_find_library(name)
                    if res:
                        return res
                    base_name = name
                    if name.startswith("lib"):
                        base_name = name[3:]
                    if "-" in base_name and not base_name.startswith("harfbuzz-subset"):
                        base_name = base_name.split("-")[0]
                    exact_path = os.path.join(homebrew_lib, f"lib{base_name}.dylib")
                    if os.path.exists(exact_path):
                        return exact_path
                    try:
                        for f in os.listdir(homebrew_lib):
                            if f.startswith(f"lib{base_name}") and f.endswith(".dylib"):
                                return os.path.join(homebrew_lib, f)
                    except Exception:
                        pass
                    return None

                ctypes.util.find_library = new_find_library

    # Suppress verbose third-party loggers unless explicitly requested
    if log_level_str != "DEBUG":
        logging.getLogger("fontTools").setLevel(logging.WARNING)
        logging.getLogger("weasyprint").setLevel(logging.WARNING)
        logging.getLogger("jpype").setLevel(logging.WARNING)

    # CLI check for WeasyPrint loading (used by GHA to validate bundling)
    if len(sys.argv) > 1 and sys.argv[1] == "--check-weasyprint":
        try:
            import weasyprint  # noqa: F401

            print("SUCCESS: WeasyPrint imported successfully.")
            sys.exit(0)
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"FAILURE: WeasyPrint import failed: {e}", file=sys.stderr)
            sys.exit(1)

    serve()
