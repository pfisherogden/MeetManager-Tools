"""Directory watcher service for ingesting live timing system result files (Issue #168)."""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

DEFAULT_TIMING_EXTENSIONS = (".json", ".csv", ".do4", ".do3", ".scb", ".txt", ".res")


class TimingResultWatcher:
    """Monitors a timing system export directory for new or modified result files.

    Attributes:
        watch_dir: Directory path to monitor for timing exports.
        on_chunk: Callback invoked as ``on_chunk(filename, content_bytes)`` for each new/updated file.
        poll_interval: Seconds between directory scans when running in background mode.
        extensions: Tuple of file extensions considered timing result files.
    """

    def __init__(
        self,
        watch_dir: str | Path,
        on_chunk: Callable[[str, bytes], Any],
        poll_interval: float = 2.0,
        extensions: tuple[str, ...] = DEFAULT_TIMING_EXTENSIONS,
    ) -> None:
        self.watch_dir = Path(watch_dir)
        self.on_chunk = on_chunk
        self.poll_interval = poll_interval
        self.extensions = tuple(ext.lower() for ext in extensions)
        self._watermarks: dict[str, tuple[int, int]] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def scan_once(self) -> int:
        """Scan ``watch_dir`` once and process any new or modified timing result files.

        Returns:
            Number of files ingested during this scan.
        """
        if not self.watch_dir.exists() or not self.watch_dir.is_dir():
            return 0

        ingested = 0
        for entry in sorted(self.watch_dir.iterdir(), key=lambda p: p.name):
            if not entry.is_file():
                continue
            if entry.name.startswith("."):
                continue
            if not entry.name.lower().endswith(self.extensions):
                continue

            try:
                stat = entry.stat()
                signature = (stat.st_mtime_ns, stat.st_size)
                if stat.st_size == 0:
                    continue
                if self._watermarks.get(entry.name) == signature:
                    continue

                content = entry.read_bytes()
                self.on_chunk(entry.name, content)
                self._watermarks[entry.name] = signature
                ingested += 1
            except OSError as exc:
                logging.warning("TimingResultWatcher failed reading %s: %s", entry.name, exc)

        return ingested

    def start(self) -> None:
        """Start monitoring ``watch_dir`` in a background daemon thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="TimingResultWatcher", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the background directory watcher thread."""
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.scan_once()
            except Exception as exc:
                logging.error("TimingResultWatcher scan error: %s", exc)
            self._stop_event.wait(self.poll_interval)


def upload_chunk_via_grpc(
    host: str,
    filename: str,
    content: bytes,
    uid: str = "desktop-user",
    access_token: str | None = None,
) -> Any:
    """Send a timing result chunk to the backend ``UploadResultChunk`` gRPC endpoint."""
    import grpc

    from meetmanager.v1 import meet_manager_pb2 as pb2
    from meetmanager.v1 import meet_manager_pb2_grpc as pb2_grpc

    token = access_token or os.getenv("DATA_ACCESS_TOKEN") or "mmtools-default-secret-2024"
    with grpc.insecure_channel(host) as channel:
        stub = pb2_grpc.MeetManagerServiceStub(channel)
        req = pb2.UploadResultChunkRequest(
            filename=filename,
            content=content,
            uid=uid,
            access_token=token,
        )
        return stub.UploadResultChunk(req, timeout=15.0)
