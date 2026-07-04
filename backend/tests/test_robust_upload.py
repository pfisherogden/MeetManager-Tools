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
