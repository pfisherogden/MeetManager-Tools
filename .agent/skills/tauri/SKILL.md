---
name: Tauri Desktop Development & Testing
description: Core guidelines and instructions for Tauri desktop development, static build integration, dynamic port discovery, and WKWebView binary download handling.
---
# Tauri Desktop Development & Testing Guidelines

## Architecture Overview
The application runs as a hybrid Tauri desktop client. The frontend is built using Next.js (prerendered to static HTML and JS via `next export`), which runs inside a native web view (WKWebView on macOS, WebView2 on Windows). The backend server runs as a Python sidecar executable packaged via PyInstaller.

## Dynamic Port Discovery
- During app startup, the Tauri native host executes the sidecar. The sidecar finds a free port to bind to (e.g. `8080` for backend services and another port like `8081` for the REST gateway).
- The sidecar writes its dynamic port mapping to a local registry file at `~/.mmtools/active_ports.json` and notifies Tauri.
- The Tauri Rust backend stores the active port in its state and exposes it to the frontend via the Tauri command `get_backend_port`.
- **CRITICAL**: The JS frontend must NEVER cache the REST port in module state across the lifetime of the application. It must call `getRestPort()` from `lib/tauri-bridge.ts` dynamically on every request to avoid race conditions during startup.

## Filesystem and Binary Download Limits
- **Problem**: WKWebView has strict sandboxing and message size limitations on macOS. Sending massive byte arrays or base64 strings over the WebView IPC channel (e.g. JSON number arrays `[1, 2, 3...]` for 5MB+ ZIP report bundles) will crash or freeze the bridge.
- **Rules**:
  1. For large file downloads (like the report pack ZIP bundles), do NOT download the file inside the WebView JS.
  2. Use the Rust custom command `copy_file_from_storage(relative_path, dest_path)`. The frontend resolves the ZIP URL, extracts the relative storage path (from the `path` URL parameter), and instructs Rust to copy the file on disk natively.
  3. Small single PDFs (under 200KB) can continue to use base64 transfers via the `save_file_to_path` command.

## Desktop Testing & Verification
- Desktop-specific E2E tests are configured in `playwright.tauri.config.ts` and target `tauri_smoke.spec.ts`.
- Run Tauri smoke tests using:
  ```bash
  npx playwright test --config playwright.tauri.config.ts
  ```
- Before committing any changes, run local formatting, linting, and type checking:
  ```bash
  just fix
  just lint
  ```

## Windows Compatibility & Dependency Packaging
1. **WeasyPrint DLLs**: WeasyPrint relies on external shared C libraries (Cairo, Pango, GObject) to compile and render PDF reports on Windows. On the Windows builder runner, these must be installed (e.g. via MSYS2 pacman `mingw-w64-x86_64-pango`) and copied into the `backend/src/mm_to_json/lib/` directory so PyInstaller bundles them. Point WeasyPrint to them at startup by setting the `WEASYPRINT_DLL_DIRECTORIES` env var.
2. **Orphan Sidecar Process Prevention**: If the Tauri host app crashes or is force-terminated, the sidecar child process can leak. Set `MONITOR_PARENT_PROCESS=true` in the sidecar's environment when spawning it from Tauri (in `lib.rs`). This enables a stdin-monitoring daemon thread in Python that will exit immediately upon parent EOF. Do NOT enable this check in headless/Docker environments.
3. **Validation**: Always run the packaged sidecar binary with `--check-weasyprint` in GHA before building the final MSI/DMG installers to catch packaging regressions early.

