import logging
import os
import shutil
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    def _sanitize_path(self, path: str) -> str:
        """Masks sensitive parts of the path (e.g. UIDs)."""
        normalized_path = path.replace("\\", "/")
        if normalized_path.startswith("users/"):
            parts = normalized_path.split("/")
            if len(parts) > 1:
                uid = parts[1]
                masked_uid = f"{uid[:4]}...{uid[-4:]}" if len(uid) > 8 else "***"
                return "/".join(["users", masked_uid] + parts[2:])
        return path

    @abstractmethod
    def list_files(self, prefix: str) -> list[str]:
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> None:
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> None:
        pass

    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        pass

    @abstractmethod
    def get_last_modified(self, remote_path: str) -> float:
        pass

    @abstractmethod
    def get_url(self, remote_path: str) -> str:
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _get_full_path(self, path: str) -> str:
        # Prevent path traversal by ensuring the resolved path is within base_dir
        base_abs = os.path.abspath(self.base_dir)
        full_path = os.path.abspath(os.path.join(base_abs, path))

        # Use normcase to handle case-insensitive and slash-agnostic comparison on Windows
        base_abs_norm = os.path.normcase(base_abs)
        full_path_norm = os.path.normcase(full_path)

        base_prefix = base_abs_norm if base_abs_norm.endswith(os.sep) else base_abs_norm + os.sep
        if not (full_path_norm == base_abs_norm or full_path_norm.startswith(base_prefix)):
            raise PermissionError(f"Path traversal attempt detected: {path}")

        return full_path

    def list_files(self, prefix: str) -> list[str]:
        full_prefix_path = self._get_full_path(prefix)
        logger.debug(f"LocalStorageProvider: list_files(prefix={self._sanitize_path(prefix)})")
        if not os.path.exists(full_prefix_path):
            logger.debug(f"LocalStorageProvider: path does not exist: {self._sanitize_path(prefix)}")
            return []

        files = []
        for root, _, filenames in os.walk(full_prefix_path):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), self.base_dir)
                files.append(rel_path.replace("\\", "/"))
        logger.debug(f"LocalStorageProvider: found {len(files)} files")
        return files

    def upload_file(self, local_path: str, remote_path: str) -> None:
        dest = self._get_full_path(remote_path)
        logger.debug(f"LocalStorageProvider: upload_file to {self._sanitize_path(remote_path)}")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(local_path, dest)
        logger.debug(f"LocalStorageProvider: successfully saved to {self._sanitize_path(remote_path)}")

    def download_file(self, remote_path: str, local_path: str) -> None:
        src = self._get_full_path(remote_path)
        logger.debug(f"LocalStorageProvider: download_file {self._sanitize_path(remote_path)}")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(src, local_path)

    def delete_file(self, remote_path: str) -> None:
        path = self._get_full_path(remote_path)
        logger.debug(f"LocalStorageProvider: delete_file {self._sanitize_path(remote_path)}")
        if os.path.exists(path):
            os.remove(path)

    def exists(self, remote_path: str) -> bool:
        path = self._get_full_path(remote_path)
        res = os.path.exists(path)
        logger.debug(f"LocalStorageProvider: exists({self._sanitize_path(remote_path)}) -> {res}")
        return res

    def get_last_modified(self, remote_path: str) -> float:
        path = self._get_full_path(remote_path)
        if os.path.exists(path):
            return os.path.getmtime(path)
        return 0.0

    def get_url(self, remote_path: str) -> str:
        # Local URLs point to the frontend's dynamic data endpoint
        # Use environment variables to avoid collisions
        frontend_url = os.getenv("FRONTEND_URL") or os.getenv("FRONTEND_PUBLIC_URL") or "http://localhost:3100"

        api_base = frontend_url
        if "localhost" in api_base or "127.0.0.1" in api_base:
            import sys

            gateway_port = None
            for mod in list(sys.modules.values()):
                if mod and hasattr(mod, "ACTUAL_REST_PORT"):
                    val = mod.ACTUAL_REST_PORT
                    if val:
                        gateway_port = str(val)
                        break
            if not gateway_port:
                gateway_port = os.getenv("BACKEND_PORT", "8081")
            api_base = f"http://localhost:{gateway_port}"

        token = os.getenv("DATA_ACCESS_TOKEN") or "mmtools-default-secret-2024"
        import urllib.parse

        safe_path = urllib.parse.quote(remote_path)
        return f"{api_base}/api/data?path={safe_path}&token={token}"


class GCSStorageProvider(StorageProvider):
    def __init__(self, bucket_name: str):
        from google.cloud import storage

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

        # Get service account email for signing (needed in Cloud Run)
        try:
            import google.auth

            _, project_id = google.auth.default()
            self.service_account_email = getattr(self.client, "service_account_email", None)
            if not self.service_account_email:
                # If Client doesn't have it, try metadata server (internal)
                import requests  # type: ignore

                r = requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
                    headers={"Metadata-Flavor": "Google"},
                    timeout=2,
                )
                if r.status_code == 200:
                    self.service_account_email = r.text
        except Exception as e:
            logger.warning(f"Could not determine service account email: {e}")
            self.service_account_email = None

    def list_files(self, prefix: str) -> list[str]:
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]

    def upload_file(self, local_path: str, remote_path: str) -> None:
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(local_path)

    def download_file(self, remote_path: str, local_path: str) -> None:
        blob = self.bucket.blob(remote_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        blob.download_to_filename(local_path)

    def delete_file(self, remote_path: str) -> None:
        blob = self.bucket.blob(remote_path)
        blob.delete()

    def exists(self, remote_path: str) -> bool:
        blob = self.bucket.blob(remote_path)
        return blob.exists()

    def get_last_modified(self, remote_path: str) -> float:
        blob = self.bucket.get_blob(remote_path)
        if blob and blob.updated:
            return blob.updated.timestamp()
        return 0.0

    def get_url(self, remote_path: str) -> str:
        # Generate a public URL or Signed URL
        import datetime

        blob = self.bucket.blob(remote_path)
        try:
            # Try to generate signed URL (requires iam.serviceAccounts.signBlob permission)
            # v4 signing is the modern standard and works in Cloud Run if SA has right roles
            url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(hours=1),
                method="GET",
                service_account_email=self.service_account_email,
                credentials=self.client._credentials,
            )

            logger.debug(
                f"Generated signed URL for {self._sanitize_path(remote_path)} (SA: {self.service_account_email})"
            )
            return url
        except Exception:
            # Fallback to relative API path that the frontend can handle
            # The frontend knows how to append its own origin and token
            logger.warning(f"Failed to generate signed URL for {self._sanitize_path(remote_path)} (Check IAM roles)")

            import urllib.parse

            safe_path = urllib.parse.quote(remote_path)
            # Return a relative path that we handle in our /api/data proxy
            return f"/api/data?path={safe_path}"
