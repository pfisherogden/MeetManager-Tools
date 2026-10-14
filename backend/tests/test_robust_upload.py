import base64


def test_robust_base64_decoding_logic():
    # Simulate how the REST Gateway parses the content field from UploadDataset body
    # Scenario 1: Pure base64 content
    raw_data = b"swim meet data content"
    base64_pure = base64.b64encode(raw_data).decode("utf-8")

    # Simulate extraction
    content_str = base64_pure
    if "," in content_str:
        content_str = content_str.split(",", 1)[1]
    decoded = base64.b64decode(content_str)
    assert decoded == raw_data

    # Scenario 2: Base64 content with Data URL prefix
    base64_with_prefix = f"data:application/octet-stream;base64,{base64_pure}"

    # Simulate extraction
    content_str2 = base64_with_prefix
    if "," in content_str2:
        content_str2 = content_str2.split(",", 1)[1]
    decoded2 = base64.b64decode(content_str2)
    assert decoded2 == raw_data

    # Scenario 3: Base64 content with a different prefix
    base64_zip_prefix = f"data:application/zip;base64,{base64_pure}"

    # Simulate extraction
    content_str3 = base64_zip_prefix
    if "," in content_str3:
        content_str3 = content_str3.split(",", 1)[1]
    decoded3 = base64.b64decode(content_str3)
    assert decoded3 == raw_data


def test_get_google_picker_config_env_resolution(monkeypatch):
    from server import get_google_picker_config

    monkeypatch.setenv("GOOGLE_API_KEY", "picker-key-123")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id-456")
    monkeypatch.setenv("GOOGLE_APP_ID", "app-id-789")

    cfg = get_google_picker_config()
    assert cfg["apiKey"] == "picker-key-123"
    assert cfg["clientId"] == "client-id-456"
    assert cfg["appId"] == "app-id-789"


def test_resolve_drive_upload_bytes_base64():
    from server import resolve_drive_upload_bytes

    payload = b'{"meet": [{"meet_name1": "Drive Test Meet"}]}'
    b64 = base64.b64encode(payload).decode("utf-8")

    result = resolve_drive_upload_bytes(content_str=f"data:application/json;base64,{b64}")
    assert result == payload


def test_resolve_drive_upload_bytes_from_drive_api(monkeypatch):
    import urllib.request

    from server import resolve_drive_upload_bytes

    expected_bytes = b"MOCK_MDB_BINARY_CONTENT"
    captured_requests = []

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return expected_bytes

    def fake_urlopen(req, timeout=60):
        captured_requests.append((req.full_url, req.get_header("Authorization"), timeout))
        return DummyResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = resolve_drive_upload_bytes(
        file_id="drive-file-abc",
        access_token="ya29.mock-token",
    )
    assert result == expected_bytes
    assert len(captured_requests) == 1
    assert (
        captured_requests[0][0]
        == "https://www.googleapis.com/drive/v3/files/drive-file-abc?alt=media&supportsAllDrives=true"
    )
    assert captured_requests[0][1] == "Bearer ya29.mock-token"


def test_resolve_drive_upload_bytes_missing_credentials():
    import pytest

    from server import resolve_drive_upload_bytes

    with pytest.raises(ValueError, match="Google access token is required"):
        resolve_drive_upload_bytes(file_id="drive-file-abc", access_token="")

    with pytest.raises(ValueError, match="Google Drive fileId is required"):
        resolve_drive_upload_bytes(file_id="", access_token="ya29.token")
