---
name: Tooling Preferences
description: Preferred tools for development and dependency management in MeetManager-Tools. Use when setting up environments or running project commands.
---

# Tooling Preferences

## Task Execution
- **Use Just**: Execute all project commands via `just`. Avoid manual shell strings for complex tasks.
- **Workflow**: Run `just --list` to discover available recipes.

## Python & Dependencies
- **Use UV**: Manage Python dependencies and virtual environments with `uv`.
- **Sync Workspace**: Run `uv sync --all-packages --dev` from the root to synchronize all workspace members.

## Frontend & Codegen
- **Node v20**: Use Node.js v20 for all frontend development.
- **Dependency First**: Always run `npm install` in `web-client/` before `just codegen` to ensure native binaries (like `grpc-tools`) are available.
- **Buf**: Use Buf for Protocol Buffer management.

## Docker & Parity
- **Optimize Context**: Maintain `.dockerignore` to exclude `node_modules`, `.venv`, and other host-side artifacts.
- **Build Caching**: Design Dockerfiles to cache dependencies separately from source code by copying `package.json` or `pyproject.toml` first.
- **Verify Locally**: Use `just verify-ci` to run the full verification pipeline in a container that mirrors the CI environment.
- **Docker Clean Room**: If local execution (especially PDF generation or Next.js builds) hangs or fails due to host environment issues, use `docker build` and `docker run` to execute in a clean environment.
- **Anti-Stall Rules**:
  - Never run interactive commands (use `-y` for `apt`, `--no-pager` for `git`).
  - **Docker**: Always use `docker-compose exec -T` (disable TTY) to avoid "the input device is not a TTY" errors in automated environments.
  - **NPX**: Always use `npx --yes <package>` to bypass the "Ok to proceed?" installation prompt.
  - **Testing**: Ensure test runners are in "run-once" mode (e.g., `vitest run` or `npm test -- --run`) to prevent them from hanging in watch mode.
  - **Piping**: If a command lacks a non-interactive flag, pipe `yes` into it: `yes | command`.
  - **Backgrounding**: Redirect stdout/stderr to files when running long-running containerized tasks in the background to prevent terminal hangs.
  - **Build Debugging**: If a build stalls for >10 minutes, use `--progress=plain` to identify the failing layer.

## Cross-Platform Reliability
- **System Libraries**: Libraries like WeasyPrint require non-Python system dependencies (e.g., `libpango`, `libffi`). These MUST be explicitly installed in `ci.Dockerfile` and `backend/Dockerfile` using `apt-get`.
- **macOS Local Dev**: When running locally on macOS, ensure `DYLD_FALLBACK_LIBRARY_PATH` includes `/opt/homebrew/lib` if system libraries are not found by `dlopen`.

## GitHub Action Triggers
- **Path Filtering**: Use native `on.push.paths` and `on.pull_request.paths` in `.github/workflows/` instead of manual `if: contains(changed_files)` checks. This ensures CI correctly triggers and reports status on PRs.
- **Ready for Review**: CI runs are often skipped on Draft PRs. Always mark a PR as "Ready for Review" to verify the final merge state.