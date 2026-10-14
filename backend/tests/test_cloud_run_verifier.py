"""Unit tests for Cloud Run post-deployment verification and log auditing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mm_to_json.cloud_run_verifier import (
    FIREBASE_CUSTOM_TOKEN_AUDIENCE,
    file_or_update_production_issue,
    format_anomaly_markdown,
    main,
    mint_firebase_custom_token,
    scan_log_entries,
)


def test_mint_firebase_custom_token_builds_valid_payload() -> None:
    """Verify mint_firebase_custom_token encodes the expected IdentityToolkit claims."""
    fake_sa = {
        "client_email": "mmtools-sa@mmtools-488404.iam.gserviceaccount.com",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
    }

    with (
        patch("mm_to_json.cloud_run_verifier.crypt.RSASigner.from_service_account_info") as mock_from_sa,
        patch(
            "mm_to_json.cloud_run_verifier.jwt.encode",
            return_value=b"header.payload.signature",
        ) as mock_encode,
    ):
        mock_signer = MagicMock()
        mock_from_sa.return_value = mock_signer

        token = mint_firebase_custom_token(
            fake_sa,
            uid="prod-test-admin",
            claims={"role": "verifier"},
            ttl_seconds=1800,
        )

        assert token == "header.payload.signature"
        mock_from_sa.assert_called_once_with(fake_sa)
        assert mock_encode.call_count == 1
        _, payload = mock_encode.call_args[0]
        assert payload["iss"] == fake_sa["client_email"]
        assert payload["sub"] == fake_sa["client_email"]
        assert payload["aud"] == FIREBASE_CUSTOM_TOKEN_AUDIENCE
        assert payload["uid"] == "prod-test-admin"
        assert payload["claims"] == {"admin": True, "role": "verifier"}
        assert payload["exp"] - payload["iat"] == 1800


def test_mint_firebase_custom_token_validation_errors() -> None:
    """Verify missing service account fields or invalid TTL raise ValueError."""
    with pytest.raises(ValueError, match="client_email"):
        mint_firebase_custom_token({"client_email": "only-email@example.com"})

    with pytest.raises(ValueError, match="ttl_seconds"):
        mint_firebase_custom_token(
            {"client_email": "a@b.com", "private_key": "key"},
            ttl_seconds=7200,
        )


def test_scan_log_entries_detects_all_anomaly_patterns() -> None:
    """Verify scan_log_entries flags ERROR+ severity and all 4 specific patterns."""
    entries: list[dict[str, Any]] = [
        {
            "timestamp": "2026-10-14T04:00:00Z",
            "severity": "INFO",
            "textPayload": "Normal startup log message",
            "resource": {"labels": {"service_name": "mmtools-backend"}},
        },
        {
            "timestamp": "2026-10-14T04:01:00Z",
            "severity": "ERROR",
            "jsonPayload": {
                "message": "Unhandled gRPC exception in handler",
                "exception": "Traceback...",
            },
            "resource": {"labels": {"service_name": "mmtools-backend"}},
        },
        {
            "timestamp": "2026-10-14T04:02:00Z",
            "severity": "DEFAULT",
            "textPayload": "Container terminated: Memory limit exceeded (2048Mi)",
            "resource": {"labels": {"service_name": "mmtools-backend"}},
        },
        {
            "timestamp": "2026-10-14T04:03:00Z",
            "severity": "WARNING",
            "textPayload": "Error: Failed to find Server Action 'x9f8a'.",
            "resource": {"labels": {"service_name": "mmtools-frontend"}},
        },
        {
            "timestamp": "2026-10-14T04:04:00Z",
            "severity": "WARNING",
            "jsonPayload": {"error": "FirebaseAuthError: Token expired"},
            "resource": {"labels": {"service_name": "mmtools-backend"}},
        },
        {
            "timestamp": "2026-10-14T04:05:00Z",
            "severity": "INFO",
            "textPayload": "jinja2.exceptions.TemplateNotFound: meet_program.html",
            "resource": {"labels": {"service_name": "mmtools-backend"}},
        },
        {
            "timestamp": "2026-10-14T04:06:00Z",
            "severity": "ERROR",
            "httpRequest": {
                "requestUrl": "https://mmtools.run.app/favicon.ico",
                "status": 404,
            },
            "textPayload": "GET /favicon.ico 404",
            "resource": {"labels": {"service_name": "mmtools-frontend"}},
        },
    ]

    anomalies = scan_log_entries(entries, min_timestamp="2026-10-14T04:00:30Z")
    assert len(anomalies) == 5

    reasons_flat = [r for item in anomalies for r in item["reasons"]]
    assert "severity>=ERROR" in reasons_flat
    assert "Memory limit exceeded" in reasons_flat
    assert "Failed to find Server Action" in reasons_flat
    assert "Token expired" in reasons_flat
    assert "TemplateNotFound" in reasons_flat


def test_file_or_update_production_issue_deduplicates() -> None:
    """Verify existing open production bug issue is commented on instead of duplicated."""
    with patch("mm_to_json.cloud_run_verifier.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # label bug
            MagicMock(returncode=0, stdout=""),  # label production
            MagicMock(
                returncode=0,
                stdout=json.dumps(
                    [
                        {
                            "number": 599,
                            "url": "https://github.com/owner/repo/issues/599",
                            "title": "[Production Alert]",
                        }
                    ]
                ),
            ),
            MagicMock(returncode=0, stdout="https://github.com/owner/repo/issues/599"),
        ]

        url = file_or_update_production_issue(
            repo="owner/repo",
            title="[Production Alert] Cloud Run Post-Deployment Verification Failed",
            body="## Report",
        )
        assert url == "https://github.com/owner/repo/issues/599"
        comment_call = mock_run.call_args_list[-1][0][0]
        assert comment_call[:4] == ["gh", "issue", "comment", "599"]


def test_cli_audit_logs_with_json_file(tmp_path: Path) -> None:
    """Verify CLI --audit-logs returns 0 when clean and 1 when anomalies exist."""
    logs_file = tmp_path / "logs.json"
    md_file = tmp_path / "report.md"

    logs_file.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2026-10-14T04:10:00Z",
                    "severity": "INFO",
                    "textPayload": "Healthy request completed",
                }
            ]
        ),
        encoding="utf-8",
    )

    rc_clean = main(
        [
            "--audit-logs",
            "--logs-json-file",
            str(logs_file),
            "--output-markdown",
            str(md_file),
            "--e2e-status",
            "passed",
        ]
    )
    assert rc_clean == 0
    assert "No log anomalies detected" in md_file.read_text(encoding="utf-8")

    logs_file.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2026-10-14T04:11:00Z",
                    "severity": "CRITICAL",
                    "textPayload": "Memory limit exceeded",
                }
            ]
        ),
        encoding="utf-8",
    )
    rc_fail = main(
        [
            "--audit-logs",
            "--logs-json-file",
            str(logs_file),
            "--output-markdown",
            str(md_file),
            "--e2e-status",
            "passed",
        ]
    )
    assert rc_fail == 1
    report_text = format_anomaly_markdown(
        scan_log_entries(json.loads(logs_file.read_text(encoding="utf-8"))),
        e2e_status="failed",
        run_url="https://github.com/owner/repo/actions/runs/123",
    )
    assert "Memory limit exceeded" in report_text
    assert "`failed`" in report_text
