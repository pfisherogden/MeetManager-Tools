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
- **Race Condition Prevention**: Tauri's startup connection loop initializes the port to `""` (instead of a default fallback like `"8081"`) and only attempts loopback TCP handshakes once the sidecar log parser has successfully captured and populated the port state.
- **CRITICAL**: The JS frontend must NEVER cache the REST port in module state across the lifetime of the application. It must call `getRestPort()` from `lib/tauri-bridge.ts` dynamically on every request to avoid race conditions during startup.

## Filesystem and Binary Download Limits & Security
- **Problem**: WKWebView has strict sandboxing and message size limitations on macOS. Sending massive byte arrays over the WebView IPC channel (e.g. JSON number arrays `[1, 2, 3...]` for ZIP report bundles) will crash or freeze the bridge.
- **Rules**:
  1. For large file downloads (like the report pack ZIP bundles), do NOT download the file inside the WebView JS. Use the Rust custom command `copy_file_from_storage(relative_path, dest_path)`. The frontend resolves the ZIP URL, extracts the relative storage path (from the `path` URL parameter), and instructs Rust to copy the file on disk natively.
  2. For writing files, do NOT pass JSON integer arrays over the IPC channel. Convert the data to a Base64 string in Javascript and decode it natively in Rust using the `base64` crate to ensure fast, sub-millisecond writes.
  3. **Path Traversal Guards**: The custom command `copy_file_from_storage` must canonicalize joined paths (`fs::canonicalize`) to resolve symlinks and relative tokens before verifying they reside strictly inside the application data directory (`starts_with`). The command `save_file_to_path` must enforce that target paths are absolute and reject any attempts to write to sensitive OS locations (e.g. home shell profiles, `.ssh`, `/etc`, `/Windows`).

## Access Database connection & Concurrency (Windows)
1. **Access Database File Locks**: On Windows, open database handles hold file locks that prevent dynamic file deletions, triggering `WinError 32 PermissionError`.
   * **Rule**: Always instantiate `MmToJsonConverter` within a context manager (`with` block) or wrap it in `try/finally` blocks calling `.close()`.
   * **Rule**: Harden the `.close()` method to verify the JVM is still active (via `jpype.isJVMStarted()`) before releasing connections, preventing interpreter teardown crashes during garbage collection destructors (`__del__`).
2. **JNI Concurrency Safety**: Bootstrapping the JVM is non-reentrant.
   * **Rule**: Protect JVM startup calls (`ensure_jvm_started`) in `mdb_writer.py` with a synchronization lock to prevent concurrent worker threads from triggering JNI runtime crashes.
3. **Singleton Thread Spawning**: Ensure background threads (like the parent process stdin monitor thread in `platform_setup.py`) are protected by a global thread lock and check-flag to prevent duplicate thread leaks.

## Desktop Testing & Verification
- Desktop-specific E2E tests are configured in `playwright.tauri.config.ts` and target `tauri_smoke.spec.ts`.
- Run Tauri smoke tests using:
  ```bash
  npx playwright test --config playwright.tauri.config.ts
  ```
- Before committing any changes, run local formatting, linting, and type checking:
  ```bash
  just fix
  ```

## Windows Dependency Packaging & Sidecar Stdin Monitoring
1. **WeasyPrint DLLs**: WeasyPrint relies on external shared C libraries (Cairo, Pango, GObject) to compile and render PDF reports on Windows. On the Windows builder runner, these must be installed (e.g. via MSYS2 pacman `mingw-w64-x86_64-pango`) and copied into the `backend/src/mm_to_json/lib/` directory so PyInstaller bundles them. Point WeasyPrint to them at startup by setting the `WEASYPRINT_DLL_DIRECTORIES` env var.
2. **Orphan Sidecar Process Prevention**: If the Tauri host app crashes or is force-terminated, the sidecar child process can leak. Set `MONITOR_PARENT_PROCESS=true` in the sidecar's environment when spawning it from Tauri (in `lib.rs`). This enables a stdin-monitoring daemon thread in Python that will exit immediately upon parent EOF. Do NOT enable this check in headless/Docker environments.
3. **Validation**: Always run the packaged sidecar binary with `--check-weasyprint` in GHA before building the final MSI/DMG installers to catch packaging regressions early.

