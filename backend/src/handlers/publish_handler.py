from __future__ import annotations

import json
import logging
import os
import tempfile
import urllib.parse
from typing import TYPE_CHECKING, Any, Protocol

import grpc

if TYPE_CHECKING:
    from storage_provider import StorageProvider


class PublishServicerContext(Protocol):
    storage: StorageProvider

    def _check_auth(self, context: grpc.ServicerContext) -> str: ...
    def _load_user_data(self, context: grpc.ServicerContext) -> tuple[dict[str, Any], dict[str, Any]]: ...


SOURCE_FILE = "Sample_Data.json"


def publish_meet_data(request: Any, context: grpc.ServicerContext, servicer: PublishServicerContext, pb2: Any) -> Any:
    """Extracts mobile judge app data and prepares public-accessible links."""
    request = request or pb2.PublishMeetDataRequest()
    uid = servicer._check_auth(context)
    cache, config = servicer._load_user_data(context)
    current_file = config.get("active_dataset", SOURCE_FILE)

    try:
        from handlers.auth_utils import get_data_access_token
        from mm_to_json.judge_app_extractor import JudgeAppExtractor
        from mm_to_json.mm_to_json import MmToJsonConverter

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
            servicer.storage.upload_file(tmp_path, user_pub_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # Generate URLs
        token = get_data_access_token()

        if request.frontend_url:
            frontend_base = request.frontend_url.rstrip("/")
        else:
            frontend_base = os.getenv("FRONTEND_URL") or os.getenv("FRONTEND_PUBLIC_URL")
            if not frontend_base:
                frontend_host = os.getenv("FRONTEND_PUBLIC_HOST", "localhost")
                frontend_port = os.getenv("FRONTEND_PORT", "3000")
                frontend_base = f"http://{frontend_host}:{frontend_port}"

        safe_pub_path = urllib.parse.quote(user_pub_path)
        program_url = f"{frontend_base}/api/data?path={safe_pub_path}&token={token}"
        sync_url = f"{frontend_base}/api/sync-dqs?token={token}&uid={uid}"

        logging.info(f"PublishMeetData: frontend_base={frontend_base}, program_url={program_url}")

        encoded_program = urllib.parse.quote(program_url, safe="")
        encoded_sync = urllib.parse.quote(sync_url, safe="")

        judge_app_base = os.getenv("JUDGE_APP_URL")
        if not judge_app_base:
            if "localhost" in frontend_base or "127.0.0.1" in frontend_base:
                judge_app_base = "http://localhost:3000/judge"
            else:
                judge_app_base = "https://pfisherogden.github.io/MeetManager-Tools/judge"

        judge_app_url = f"{judge_app_base}?program_url={encoded_program}&sync_url={encoded_sync}"
        return pb2.PublishMeetDataResponse(success=True, message="Published", judge_app_url=judge_app_url)
    except Exception as e:
        logging.error(f"Publish failed: {e}")
        return pb2.PublishMeetDataResponse(success=False, message=str(e))
