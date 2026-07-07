from __future__ import annotations

import datetime
import os

import pytz


def test_windows_format_string():
    # Verify that the standard strftime format string is safe on the current platform
    tz = pytz.timezone("America/Los_Angeles")
    now = datetime.datetime.now(tz)

    # Detect platform-safe strftime format string
    fmt = "%#I:%M %p %#m/%#d/%Y" if os.name == "nt" else "%-I:%M %p %-m/%-d/%Y"
    try:
        gen_time = now.strftime(fmt)
        assert len(gen_time) > 0
    except ValueError as e:
        raise AssertionError(f"Format string '{fmt}' is invalid on {os.name}: {e}") from e


def test_path_normalization_list_datasets():
    # Simulate Windows backslash path list
    windows_paths = [
        "users\\e2e-default-user\\config.json",
        "users\\e2e-default-user\\Singers23.mdb",
    ]

    # Verify that normalizing paths to forward slashes resolves path components correctly
    parsed_files = []
    for rel_path in windows_paths:
        normalized_path = rel_path.replace("\\", "/")
        parts = normalized_path.split("/")
        if len(parts) == 3:
            parsed_files.append(parts[2])

    assert "Singers23.mdb" in parsed_files
    assert "config.json" in parsed_files


def test_setup_platform_env_windows():
    from unittest.mock import patch

    from mm_to_json.platform_setup import setup_platform_env

    # Mock os.name to simulate Windows and os.path.exists to simulate found JRE lib folder
    # We set MONITOR_PARENT_PROCESS to false to avoid starting parent process monitor thread in test
    with (
        patch("os.name", "nt"),
        patch("os.path.exists", return_value=True),
        patch.dict("os.environ", {"MONITOR_PARENT_PROCESS": "false"}),
    ):
        import os

        setup_platform_env()
        assert "WEASYPRINT_DLL_DIRECTORIES" in os.environ
        assert os.environ["WEASYPRINT_DLL_DIRECTORIES"].endswith("lib")
        assert os.environ["WEASYPRINT_DLL_DIRECTORIES"] in os.environ["PATH"]
