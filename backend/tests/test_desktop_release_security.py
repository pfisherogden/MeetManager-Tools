"""Guard against shipping a debuggable desktop app.

The Windows installer is built from ``web-client/src-tauri`` and published to the
public "latest" release. A ``--remote-debugging-port`` baked into any Tauri config
(for example ``tauri.windows.conf.json``) would ship Chromium remote debugging, an
unauthenticated control channel for the app's WebView, to every user. The E2E suite
must pass the port at *runtime* through ``WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS``
(see ``web-client/tests-e2e/tauri.fixture.ts``) instead.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TAURI_DIR = REPO_ROOT / "web-client" / "src-tauri"


def test_no_remote_debugging_port_in_tauri_configs() -> None:
    """No Tauri config (base or per-platform override) may enable remote debugging."""
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in TAURI_DIR.glob("tauri*.json")
        if "remote-debugging" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"Remote debugging must not be baked into the shipped app: {offenders}"


def test_no_windows_platform_override_config() -> None:
    """The Windows override file existed solely to bake in the debug port."""
    assert not (TAURI_DIR / "tauri.windows.conf.json").exists()


def test_release_workflow_does_not_set_debug_port_job_wide() -> None:
    """A job-level WEBVIEW2 debug arg would apply to every step, including the installer build."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "desktop-build.yml").read_text(encoding="utf-8")
    top_level_env = workflow.split("\njobs:", 1)[0]
    assert "remote-debugging-port" not in top_level_env
