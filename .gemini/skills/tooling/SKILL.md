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
- **Mobile CI**: When building managed Expo web artifacts in GitHub Actions, always use `npm ci --legacy-peer-deps` to bypass strict upstream peer dependency conflicts (e.g., React 19 vs Expo) that will otherwise break automated CI pipelines.
- **Buf**: Use Buf for Protocol Buffer management.
- **Tailwind CSS v4 Compatibility**: When migrating a Next.js project to Tailwind CSS v4, traditional `tailwind.config.ts` setups (especially those used by component libraries like Shadcn) will fail during production builds (`next build`) due to missing `@theme` variable definitions. Ensure `globals.css` strictly utilizes the `@theme inline` block syntax to expose design system tokens (e.g., `--border`, `--background`) to the v4 compiler.

## Deployment
- **GitHub Pages**: Automate via GitHub Actions using `peaceiris/actions-gh-pages`.
- **Manual Push**: If CI is unavailable, use `git subtree push --prefix <app-dir>/dist origin gh-pages` to deploy build artifacts directly to the hosting branch.
- **Asset Handling**: Always verify that binary assets (icons, splash screens) are correctly committed to the source branch before triggering a build.

## Docker & Parity
- **Optimize Context**: Maintain `.dockerignore` to exclude `node_modules`, `.venv`, and other host-side artifacts.
- **Build Caching**: Design Dockerfiles to cache dependencies separately from source code by copying `package.json` or `pyproject.toml` first.
- **Verify Locally**: Use `just verify-ci` to run the full verification pipeline in a container that mirrors the CI environment.
- **Local CI**: Use `act` (via `just ci-local`) to run GitHub Actions locally. This helps identify environment-specific failures (e.g., missing system libs in CI) without waiting for remote runs.
- **Docker Clean Room**: If local execution (especially PDF generation or Next.js builds) hangs or fails due to host environment issues, use `docker build` and `docker run` to execute in a clean environment.
- **Anti-Stall Rules**:
  - Never run interactive commands (use `-y` for `apt`, `--no-pager` for `git`).
  - **Docker**: Always use `docker-compose exec -T` (disable TTY) to avoid "the input device is not a TTY" errors in automated environments.
  - **NPX**: Always use `npx --yes <package>` to bypass the "Ok to proceed?" installation prompt.
  - **Mypy**: Use `--install-types --non-interactive` **together**. Using only one will still result in an interactive prompt or a fatal error if stubs are missing.
  - **Testing**: Ensure test runners are in "run-once" mode (e.g., `vitest run` or `npm test -- --run`) to prevent them from hanging in watch mode.
  - **Piping**: If a command lacks a non-interactive flag, pipe `yes` into it: `yes | command`.
  - **Backgrounding**: Redirect stdout/stderr to files when running long-running containerized tasks in the background to prevent terminal hangs.
  - **Build Debugging**: If a build stalls for >10 minutes, use `--progress=plain` to identify the failing layer.

## Cross-Platform Reliability
- **System Libraries**: Libraries like WeasyPrint require non-Python system dependencies (e.g., `libpango`, `libffi`). These MUST be explicitly installed in `ci.Dockerfile` and `backend/Dockerfile` using `apt-get`.
- **macOS Local Dev**: When running locally on macOS, ensure `DYLD_FALLBACK_LIBRARY_PATH` includes `/opt/homebrew/lib` if system libraries are not found by `dlopen`.
- **CI Pathing**: Always set `PYTHONPATH=backend/src` (or appropriate source root) when running Python tests or scripts in CI to avoid `ModuleNotFoundError`.

## GitHub Action Triggers
- **Path Filtering**: Use native `on.push.paths` and `on.pull_request.paths` in `.github/workflows/` instead of manual `if: contains(changed_files)` checks. This ensures CI correctly triggers and reports status on PRs.
- **Ready for Review**: CI runs are often skipped on Draft PRs. Always mark a PR as "Ready for Review" to verify the final merge state.