import logging
import os
import shutil
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
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

        if not full_path.startswith(base_abs):
            raise PermissionError(f"Path traversal attempt detected: {path}")

        return full_path

    def list_files(self, prefix: str) -> list[str]:
        full_prefix_path = self._get_full_path(prefix)
        if not os.path.exists(full_prefix_path):
            return []

        files = []
        for root, _, filenames in os.walk(full_prefix_path):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), self.base_dir)
                files.append(rel_path)
        return files

    def upload_file(self, local_path: str, remote_path: str) -> None:
        dest = self._get_full_path(remote_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(local_path, dest)

    def download_file(self, remote_path: str, local_path: str) -> None:
        src = self._get_full_path(remote_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(src, local_path)

    def delete_file(self, remote_path: str) -> None:
        path = self._get_full_path(remote_path)
        if os.path.exists(path):
            os.remove(path)

    def exists(self, remote_path: str) -> bool:
        return os.path.exists(self._get_full_path(remote_path))

    def get_last_modified(self, remote_path: str) -> float:
        path = self._get_full_path(remote_path)
        if os.path.exists(path):
            return os.path.getmtime(path)
        return 0.0

    def get_url(self, remote_path: str) -> str:
        # Local URLs point to the frontend's dynamic data endpoint
        # Use environment variables to avoid collisions
        host = os.getenv("FRONTEND_PUBLIC_HOST", "localhost")
        port = os.getenv("FRONTEND_PORT", "3000")
        return f"http://{host}:{port}/api/data?path={remote_path}"


class GCSStorageProvider(StorageProvider):
    def __init__(self, bucket_name: str):
        from google.cloud import storage

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

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
        # For simplicity in this project, we'll use public URL if bucket is public,
        # but better to use Signed URL for 1 hour.
        blob = self.bucket.blob(remote_path)
        try:
            # Try to generate signed URL (requires credentials with service account)
            return blob.generate_signed_url(expiration=3600, method="GET")
        except Exception:
            # Fallback to public URL
            return blob.public_url
