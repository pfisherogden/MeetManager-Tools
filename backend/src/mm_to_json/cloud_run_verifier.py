"""Automated Cloud Run post-deployment verification and log anomaly detection.

Provides utilities to:
1. Mint short-lived Firebase Custom Token JWTs using service account credentials.
2. Query and scan Cloud Run logs for error severities and production anomaly patterns.
3. Format Markdown incident reports and file/update deduplicated GitHub issues.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from google.auth import crypt, jwt

FIREBASE_CUSTOM_TOKEN_AUDIENCE = (
    "https://identitytoolkit.googleapis.com/google.identity.identitytoolkit.v1.IdentityToolkit"
)

ERROR_SEVERITIES: frozenset[str] = frozenset({"ERROR", "CRITICAL", "ALERT", "EMERGENCY"})

ANOMALY_PATTERNS: tuple[str, ...] = (
    "Memory limit exceeded",
    "Failed to find Server Action",
    "Token expired",
    "TemplateNotFound",
)


def mint_firebase_custom_token(
    service_account_info: dict[str, Any],
    uid: str = "prod-test-admin",
    claims: dict[str, Any] | None = None,
    ttl_seconds: int = 3600,
) -> str:
    """Mint a short-lived Firebase Custom Token JWT using a service account key.

    Args:
        service_account_info: Parsed JSON dictionary of a GCP service account key.
        uid: The Firebase UID to assign to the custom token.
        claims: Optional custom claims dictionary (defaults to ``{"admin": True}``).
        ttl_seconds: Token lifetime in seconds (max 3600).

    Returns:
        Signed JWT string suitable for ``signInWithCustomToken``.

    Raises:
        ValueError: If required fields are missing from ``service_account_info``
            or ``ttl_seconds`` is invalid.
    """
    client_email = service_account_info.get("client_email")
    private_key = service_account_info.get("private_key")
    if not client_email or not private_key:
        raise ValueError("service_account_info must contain 'client_email' and 'private_key'")
    if ttl_seconds <= 0 or ttl_seconds > 3600:
        raise ValueError("ttl_seconds must be between 1 and 3600")

    now = int(time.time())
    merged_claims = {"admin": True}
    if claims:
        merged_claims.update(claims)

    payload: dict[str, Any] = {
        "iss": client_email,
        "sub": client_email,
        "aud": FIREBASE_CUSTOM_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + ttl_seconds,
        "uid": uid,
        "claims": merged_claims,
    }

    signer = crypt.RSASigner.from_service_account_info(service_account_info)
    encoded = jwt.encode(signer, payload)
    if isinstance(encoded, bytes):
        return encoded.decode("utf-8")
    return str(encoded)


def extract_log_message(entry: dict[str, Any]) -> str:
    """Extract a searchable text message from a Cloud Logging entry dictionary.

    Args:
        entry: A single log entry dictionary returned by ``gcloud logging read``.

    Returns:
        Combined message string extracted from ``textPayload``, ``jsonPayload``,
        or ``protoPayload``.
    """
    parts: list[str] = []

    text_payload = entry.get("textPayload")
    if isinstance(text_payload, str) and text_payload.strip():
        parts.append(text_payload.strip())

    json_payload = entry.get("jsonPayload")
    if isinstance(json_payload, dict):
        for key in ("message", "exception", "error", "msg", "detail"):
            val = json_payload.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
        if not parts:
            parts.append(json.dumps(json_payload, sort_keys=True))

    proto_payload = entry.get("protoPayload")
    if isinstance(proto_payload, dict):
        status = proto_payload.get("status")
        if isinstance(status, dict) and status.get("message"):
            parts.append(str(status["message"]))
        elif not parts:
            parts.append(json.dumps(proto_payload, sort_keys=True))

    return "\n".join(parts)


def _is_benign_entry(entry: dict[str, Any], message: str) -> bool:
    """Return True if the log entry is a known benign probe (e.g. favicon 404)."""
    http_req = entry.get("httpRequest")
    if isinstance(http_req, dict):
        req_url = str(http_req.get("requestUrl", ""))
        status = http_req.get("status")
        if "/favicon.ico" in req_url and status in (404, 499):
            return True
    if "/favicon.ico" in message and "404" in message:
        return True
    return False


def scan_log_entries(
    entries: list[dict[str, Any]],
    min_timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Scan Cloud Run log entries for error severities and anomaly patterns.

    Args:
        entries: List of Cloud Logging entry dicts.
        min_timestamp: Optional ISO-8601 UTC timestamp string used to filter out
            older log entries from prior deployments.

    Returns:
        List of detected anomaly dictionaries with keys ``timestamp``,
        ``severity``, ``service``, ``reasons``, and ``snippet``.
    """
    anomalies: list[dict[str, Any]] = []

    for entry in entries:
        timestamp = str(entry.get("timestamp") or entry.get("receiveTimestamp") or "")
        if min_timestamp and timestamp and timestamp < min_timestamp:
            continue

        severity = str(entry.get("severity") or "DEFAULT").upper()
        message = extract_log_message(entry)
        if _is_benign_entry(entry, message):
            continue

        reasons: list[str] = []
        if severity in ERROR_SEVERITIES:
            reasons.append(f"severity>={severity}")

        for pattern in ANOMALY_PATTERNS:
            if pattern.lower() in message.lower():
                reasons.append(pattern)

        if not reasons:
            continue

        resource = entry.get("resource")
        service_name = "unknown"
        if isinstance(resource, dict):
            labels = resource.get("labels")
            if isinstance(labels, dict):
                service_name = str(labels.get("service_name") or "unknown")

        snippet = message if message else json.dumps(entry, sort_keys=True)
        if len(snippet) > 500:
            snippet = snippet[:497] + "..."

        anomalies.append(
            {
                "timestamp": timestamp,
                "severity": severity,
                "service": service_name,
                "reasons": reasons,
                "snippet": snippet,
            }
        )

    return anomalies


def fetch_cloud_run_logs(
    project_id: str,
    region: str,
    services: list[str],
    lookback_minutes: int = 20,
    min_timestamp: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Fetch recent Cloud Run logs using ``gcloud logging read``.

    Args:
        project_id: Google Cloud project ID.
        region: Cloud Run region (e.g. ``us-west1``).
        services: Cloud Run service names to query.
        lookback_minutes: Number of minutes in the past to query if
            ``min_timestamp`` is not provided.
        min_timestamp: Optional ISO-8601 UTC timestamp lower bound.
        limit: Maximum number of log entries to retrieve.

    Returns:
        Parsed list of Cloud Logging entry dicts.
    """
    if min_timestamp:
        cutoff = min_timestamp
    else:
        dt = datetime.now(UTC) - timedelta(minutes=lookback_minutes)
        cutoff = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    service_clauses = " OR ".join(f'resource.labels.service_name="{svc}"' for svc in services)
    log_filter = (
        'resource.type="cloud_run_revision" '
        f'AND resource.labels.location="{region}" '
        f"AND ({service_clauses}) "
        f'AND timestamp>="{cutoff}"'
    )

    cmd = [
        "gcloud",
        "logging",
        "read",
        log_filter,
        f"--project={project_id}",
        f"--limit={limit}",
        "--format=json",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        err_detail = getattr(exc, "stderr", "") or str(exc)
        print(
            f"Warning: gcloud logging read failed (continuing with empty log entries): {err_detail.strip()}",
            file=sys.stderr,
        )
        return []

    raw = res.stdout.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def format_anomaly_markdown(
    anomalies: list[dict[str, Any]],
    e2e_status: str = "passed",
    run_url: str | None = None,
    max_entries: int = 15,
) -> str:
    """Format a Markdown summary report for post-deployment verification results.

    Args:
        anomalies: Detected anomaly dictionaries from ``scan_log_entries``.
        e2e_status: Status of the Playwright E2E suite (``passed`` or ``failed``).
        run_url: Optional URL to the GitHub Actions workflow run.
        max_entries: Maximum number of log snippets to include.

    Returns:
        Formatted Markdown report string.
    """
    lines: list[str] = [
        "## Automated Cloud Run Post-Deployment Verification Report",
        "",
        f"- **Playwright Production E2E Status**: `{e2e_status}`",
        f"- **Detected Log Anomalies**: `{len(anomalies)}`",
    ]
    if run_url:
        lines.append(f"- **Workflow Run**: {run_url}")
    lines.append("")

    if anomalies:
        lines.append("### Detected Log Anomalies")
        lines.append("")
        for idx, item in enumerate(anomalies[:max_entries], start=1):
            reasons_str = ", ".join(item["reasons"])
            lines.append(
                f"{idx}. **`{item['service']}`** | `{item['severity']}` | "
                f"`{item['timestamp']}` | Triggers: `{reasons_str}`"
            )
            lines.append("   ```text")
            for snippet_line in str(item["snippet"]).splitlines():
                lines.append(f"   {snippet_line}")
            lines.append("   ```")
        if len(anomalies) > max_entries:
            remaining = len(anomalies) - max_entries
            lines.append(f"\n*...and {remaining} additional anomaly entries omitted.*")
    else:
        lines.append("No log anomalies detected in the inspection window.")

    return "\n".join(lines)


def file_or_update_production_issue(
    repo: str,
    title: str,
    body: str,
) -> str | None:
    """Create or update a deduplicated GitHub issue with ``bug`` and ``production`` labels.

    Args:
        repo: GitHub repository in ``owner/name`` format.
        title: Issue title for new issues.
        body: Markdown body describing the verification failure.

    Returns:
        The URL of the created or updated GitHub issue, or ``None`` on error.
    """
    for label, color, desc in (
        ("bug", "d73a4a", "Something isn't working"),
        ("production", "b60205", "Production Cloud Run verification failure"),
    ):
        subprocess.run(
            [
                "gh",
                "label",
                "create",
                label,
                "--repo",
                repo,
                "--color",
                color,
                "--description",
                desc,
                "--force",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    list_res = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--label",
            "production",
            "--label",
            "bug",
            "--state",
            "open",
            "--json",
            "number,url,title",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if list_res.returncode == 0 and list_res.stdout.strip():
        try:
            open_issues = json.loads(list_res.stdout)
            if isinstance(open_issues, list) and open_issues:
                issue_num = str(open_issues[0]["number"])
                issue_url = str(open_issues[0].get("url") or "")
                subprocess.run(
                    [
                        "gh",
                        "issue",
                        "comment",
                        issue_num,
                        "--repo",
                        repo,
                        "--body",
                        body,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return issue_url
        except (json.JSONDecodeError, KeyError, subprocess.CalledProcessError):
            pass

    try:
        create_res = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--body",
                body,
                "--label",
                "bug",
                "--label",
                "production",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return create_res.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        err_detail = getattr(exc, "stderr", "") or str(exc)
        print(
            f"Warning: failed to create GitHub issue via gh CLI: {err_detail.strip()}",
            file=sys.stderr,
        )
        return None


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Cloud Run post-deployment verification."""
    parser = argparse.ArgumentParser(description="Cloud Run post-deployment verification and log auditor.")
    parser.add_argument(
        "--mint-custom-token",
        action="store_true",
        help="Mint a Firebase Custom Token JWT from GCP_SA_KEY or --sa-key-file.",
    )
    parser.add_argument(
        "--sa-key-file",
        type=str,
        default=None,
        help="Path to a service account JSON file.",
    )
    parser.add_argument(
        "--uid",
        type=str,
        default="prod-test-admin",
        help="UID for the minted Firebase Custom Token.",
    )
    parser.add_argument(
        "--audit-logs",
        action="store_true",
        help="Audit Cloud Run logs for anomalies.",
    )
    parser.add_argument("--project", type=str, default="mmtools-488404")
    parser.add_argument("--region", type=str, default="us-west1")
    parser.add_argument(
        "--services",
        nargs="+",
        default=["mmtools-backend", "mmtools-frontend"],
    )
    parser.add_argument("--lookback-minutes", type=int, default=20)
    parser.add_argument("--min-timestamp", type=str, default=None)
    parser.add_argument(
        "--logs-json-file",
        type=str,
        default=None,
        help="Optional local JSON file of log entries instead of querying gcloud.",
    )
    parser.add_argument("--e2e-status", type=str, default="passed")
    parser.add_argument("--run-url", type=str, default=None)
    parser.add_argument("--output-markdown", type=str, default=None)
    parser.add_argument("--auto-file-issue", action="store_true")
    parser.add_argument(
        "--repo",
        type=str,
        default=os.environ.get("GITHUB_REPOSITORY", "pfisherogden/MeetManager-Tools"),
    )

    args = parser.parse_args(argv)

    if args.mint_custom_token:
        raw_key = os.environ.get("GCP_SA_KEY", "")
        if args.sa_key_file:
            raw_key = Path(args.sa_key_file).read_text(encoding="utf-8")
        if not raw_key:
            print(
                "Error: GCP_SA_KEY environment variable or --sa-key-file is required",
                file=sys.stderr,
            )
            return 1
        sa_info = json.loads(raw_key)
        token = mint_firebase_custom_token(sa_info, uid=args.uid)
        print(token)
        return 0

    if args.audit_logs:
        if args.logs_json_file:
            entries = json.loads(Path(args.logs_json_file).read_text(encoding="utf-8"))
        else:
            entries = fetch_cloud_run_logs(
                project_id=args.project,
                region=args.region,
                services=args.services,
                lookback_minutes=args.lookback_minutes,
                min_timestamp=args.min_timestamp,
            )

        anomalies = scan_log_entries(entries, min_timestamp=args.min_timestamp)
        report_md = format_anomaly_markdown(
            anomalies=anomalies,
            e2e_status=args.e2e_status,
            run_url=args.run_url,
        )

        if args.output_markdown:
            Path(args.output_markdown).write_text(report_md, encoding="utf-8")
        else:
            print(report_md)

        has_failure = bool(anomalies) or args.e2e_status.lower() != "passed"
        if has_failure and args.auto_file_issue:
            title = "[Production Alert] Cloud Run Post-Deployment Verification Failed"
            file_or_update_production_issue(
                repo=args.repo,
                title=title,
                body=report_md,
            )
        return 1 if has_failure else 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
