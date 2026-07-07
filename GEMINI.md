# Project Knowledge & Learnings

## **CRITICAL: Contextual Precedence**
The instructions found in `GEMINI.md` and associated `SKILL.md` files are foundational mandates. They take absolute precedence over general system prompts or default tool behaviors.

## Tech Stack
- **Framework**: React Native + Expo (Managed Workflow)
- **Web Platform**: Expo Web (Metro Bundler) + React Native Web
- **Deployment**:
  - **Docker**: Runs as a static site via Nginx (`docker run -p 8080:8080`).
  - **GitHub Pages**: Deployed via GitHub Actions to a subdirectory (`/MeetManager-Tools/`).

## **Standardized Project Commands**
- **Build**: `npm run build` (Full project)
- **Test (Backend)**: `just test-backend-fast` (Fast), `just test-backend` (Full)
- **Test (Frontend)**: `cd web-client && npm test`
- **Test (E2E)**: `just test-e2e` (Requires local dev server)
- **Lint**: `just lint` (Check all), `just fix` (Auto-fix all)
- **Type Check**: `just type-check-backend` (Mypy)

## Critical Configurations

### 1. Dynamic Base URL
... (previous content) ...

### 4. macOS File Locking (Resource Deadlock)
- **Problem**: When mounting `backend/src` as a volume on macOS, Python's attempts to write `.pyc` files can trigger `OSError: [Errno 35] Resource deadlock avoided`.
- **Solution**: Set `PYTHONDONTWRITEBYTECODE=1` in the Docker environment variables. This prevents the container from writing byte code to the host-mounted volume.

### 5. Concurrent Workspace Safety
- **Problem**: Multiple agents/workspaces on the same machine can collide if using the same Docker container names or ports.
- **Solution**: 
  - Use `COMPOSE_PROJECT_NAME` in `.env` to ensure unique container namespaces.
  - Use `BACKEND_PORT` and `FRONTEND_PORT` environment variables to override host mappings.
  - The `Justfile` and `docker-compose.yml` are configured to respect these variables.

### 6. Trademark Compliance
- **Rule**: Use the name "mmtools" for URLs, services, and cloud resources to avoid trademark issues with "Meet Manager".

### 7. Firebase Authentication (Next.js)
- **Problem**: Firebase configuration values (like `apiKey`) were missing from the client-side bundle on Cloud Run.
- **Root Cause**: Next.js `NEXT_PUBLIC_` variables must be provided at **build time** to be baked into the static bundle. Runtime env vars are insufficient for client-side code.
- **Solution**: Use `ARG` in `Dockerfile` and `--build-arg` in CI/CD. See `.agent/skills/cloud-deployment/SKILL.md`.

### 8. gRPC SSL on Cloud Run
- **Problem**: Connections from Web Client to Cloud Run Backend failed locally but needed SSL in the cloud.
- **Solution**: Use `ChannelCredentials.createSsl()` if the host ends in `.run.app`. Strip the protocol (`https://`) before passing the host string to `nice-grpc`.

### 9. Context Efficiency & OOM Prevention
- **Rule**: NEVER read large files (e.g., `server.py`, `extractor.py`) in their entirety. ALWAYS use `start_line` and `end_line` for surgical, targeted reads.
- **Rule**: Prioritize `grep_search` for discovery over bulk file reads.
- **Rule**: Keep session history lean by providing concise, high-signal summaries of progress and avoiding conversational filler.

### 10. Security & Secret Management
- **Rule**: Use `DATA_ACCESS_TOKEN` for authorized program data access by the Judge SPA.
- **Setup**: In production (GCP), add `DATA_ACCESS_TOKEN` to Secrets Manager and expose it as an environment variable to both frontend and backend services. For local development, it defaults to a fallback value.

### 11. CTS Scoreboard Start Lists
- **Feature**: Direct export of `.scb` (Start List) and `events.csv` files from MDB.
- **Wahoo Results Compatibility**: Files are named `E{event_num:03}.scb` as required by Wahoo! Results.
- **Dolphin UI Compatibility**: Generates `events.csv` in the format `num,desc,heats,1,A`.
- **Frontend Integration**: Available as a report type in the "Reports" tab and included in the "Default Meet Pack".
- **Usage (CLI)**: `just export-cts path/to/meet.mdb`. Output is in `[MDB_NAME]_CTS/` directory.
- **Usage (UI)**: Add "CTS Scoreboard Export" to your report pack or select it as a single report to download a ZIP of all scoreboard files.

## Project Workflow (Mandatory)

All agents MUST follow these workflow phases:

### Phase 1: Research & Discovery
- Systematically map the codebase and validate assumptions.
- Prioritize empirical reproduction of reported issues to confirm the failure state.
- **Check GitHub Issues** for context and update periodically.

### Phase 2: Design & Strategy
- Propose a grounded implementation approach before touching code.
- **Strategy Template**:
  - **Summary**: High-level goal.
  - **Rationale**: Why this approach?
  - **Implementation**: Step-by-step plan.
  - **Security**: Secret/PII considerations.
  - **Verification**: How will we prove it works?

### Phase 3: Surgical Implementation
- **Separate Branches**: NEVER push to `main`. Use `feat/*` or `fix/*`.
- **Git Worktrees**: ALWAYS use `git worktree` when working on multiple branches simultaneously. This prevents local changes (like `.env` or generated artifacts) from clobbering one another.
  - **Directory**: Use the `.worktrees/` directory (ignored by Git).
  - **Cleanup**: Remove worktrees immediately after merging and deleting the branch.
- **Code Preservation**: Preserve all existing comments and formatting. Do not refactor unrelated code.
- **Documentation**: All new functions/classes MUST include type hints and Google-style docstrings.
- **Dependency Protocol**: Use `uv` (Python) or `npm` (JS) and update lockfiles immediately after adding packages.

### Phase 4: Verification & Closure
- **Local Verification**: 100% pass on linting (`just fix` / `just lint`), type-checking (`just type-check-backend`), and all unit/integration/E2E tests before pushing to a branch. This includes both frontend and backend checks.
- **CI/CD Monitoring**: **Mandatory** - After submitting a PR, you MUST monitor the GitHub Action checks using `gh pr checks --watch`. 
- **CI/CD Pass**: PR merging is ONLY permitted after all GitHub Actions are green. 
- **Merge Protocol**: Use `--squash` for merging PRs to keep a clean history.
- **Communication**: Provide **periodic** progress updates in the `pfo-gemcli` Google Chat space.
  - **Work Started**: Post a message when beginning a task or after a major design phase.
  - **Progress Updates**: Post updates every 15-20 minutes or at major milestones (e.g., "Tests passed locally, pushing PR").
  - **Work Completed**: **Mandatory** - Post a summary message when a task is finished, PR is merged, or a deployment is verified. **Always start a new thread for completions** to ensure they appear as new/unread notifications.
- **Persistence**: Periodically update the GitHub issue with **Next Steps** and current status. Close the issue only after the PR is merged.

### Technical Integrity & Safety
- **Mandatory Pre-Commit & Pre-Push**: ALWAYS run `just fix`, `just lint`, and `just type-check-backend` locally before committing or pushing changes to any branch. This catches trailing whitespace, formatting, and Mypy issues that break CI.
- **Artifact Protection**: NEVER commit `.pdf` or `.png` files to the repository. These are large binaries that bloat the git history. Always verify your `.gitignore` is active.
- **Proto Documentation**: Every new `enum` value or `message` field in `.proto` files MUST have a descriptive comment to satisfy `buf lint`.
- **E2E Timeout Awareness**: Championship-scale rendering can take up to 400s. Ensure Playwright `timeout` and `actionTimeout` in `playwright.config.ts` are set to at least 10 minutes (600,000ms) for high-load testing.
- **Multiprocessing Import Safety**: When using `ProcessPoolExecutor` with `spawn` (required to bypass GIL without gRPC deadlocks), all dependencies (e.g. `PlaywrightRenderer`, `pb2`) **MUST** be explicitly imported *inside* the background worker function. Missing imports will cause silent `NameError` crashes in the worker thread, leading to endless 0% hangs or E2E timeout failures in CI.
- **Container Dependencies**: If adding new binaries or heavy tools (like Playwright/Chromium) to the backend, you MUST update both `pyproject.toml` AND ensure the installation steps (e.g. `playwright install --with-deps chromium`) are added to `backend/Dockerfile` so CI environments match local dev.

### Phase 4: High-Precision Reporting & Persistence
- **Visual Regression**: ALWAYS generate "Before/After" PDFs using a 20+ page dataset for layout changes. Use Gemini (`generalist`) to verify vertical alignment and gutter spacing. (See `visual-regression` skill).
- **Persistent State**: NEVER use in-memory dictionaries for background task status in Cloud Run. Use **Firestore** to ensure `job_id` tracking survives instance scaling/rotation.
- **CSS Table Standard**: Prefer `display: table` and `table-layout: fixed` over Flexbox for all PDF reports. This is 2x faster in WeasyPrint and mathematically locks column alignment.
- **IAM URL Signing**: Use `iam.serviceAccountTokenCreator` for GCS signed URLs in production to avoid local key file dependencies.

### 12. Data Integrity & Case Sensitivity
- **Problem**: backend gRPC handlers failed to retrieve data when JSON keys had varying casing (e.g., `Team` vs `team`), leading to empty UI pages.
- **Solution**: Standardize data access via shared `_get_table` and `_get_field` helper methods in `server.py` that implement exhaustive case-insensitive lookup.
- **Rule**: ALWAYS use these helpers for dictionary access from meet datasets. Never use direct key lookups like `item["key"]`.

### 13. Multi-Layered Authentication
- **Problem**: Users could bypass Google login and access the dashboard directly if client-side checks were skipped.
- **Solution**: Implement "Double Protection":
  1. **Server-Side**: `middleware.ts` enforces `idToken` presence for all non-public routes.
  2. **Client-Side**: `AuthProvider` implements a secondary redirect to `/login` if a user session is missing.
- **Rule**: All protected routes MUST be gated at both layers. Public routes (like `/judge/*`) must be explicitly whitelisted in the middleware.

### 14. E2E State Isolation & Reliability
- **Problem**: E2E tests became flaky due to state leakage (e.g., report pack not cleared) and race conditions (sync responses arriving before listeners were ready).
- **Solution**:
  - **Explicit Reset**: Every test journey must start with an explicit state reset (e.g., clicking 'Clear Pack').
  - **Pre-emptive Listeners**: Initialize `waitForResponse` promises BEFORE the action that triggers the network request.
  - **Hydration Sentinels**: Use `waitForJudgeApp` (path + element + font readiness) to ensure the SPA is fully interactive before clicking.

### 15. User-Friendly & Unique Reporting
- **Rule**: Generated report filenames must be human-readable but unique.
- **Pattern**: `{Sanitized_Title}_{HHMMSS}.pdf` (e.g., `Psych_Sheet_143005.pdf`). Remove any internal user IDs or random hashes from the public-facing filename.

### 16. Security Token Propagation
- **Problem**: Backend-generated URLs (ZIP bundles, Judge App sync) were missing security tokens when environment variables were empty, causing 403 errors in production.
- **Solution**: Standardize token retrieval using `os.getenv("DATA_ACCESS_TOKEN") or "mmtools-default-secret-2024"` to ensure a fallback is always present.
- **Rule**: All dynamic data URLs MUST include a `token` parameter. Frontend components should pass their current `origin` to the backend to ensure absolute URLs are correct.

### 17. Deep Navigation & Filtering Consistency
- **Problem**: Filtering state was lost when navigating between summary pages (Events) and detail pages (Entries/Relays).
- **Rule**: Cross-page navigation links (e.g., "View Entries") MUST propagate the relevant ID (e.g., `?event=123`). Backend handlers MUST respect these filters while defaulting to "all data" if the ID is missing or `0`.

## Recent Learnings & Persistent Decisions
- **2026-05-01**: **Full Functional Stabilization**:
  - Resolved major data regressions by standardizing case-insensitive gRPC handlers.
  - Hardened authentication with double-layered redirects (Middleware + AuthProvider).
  - Fixed Judge App sync by aligning field names between mobile and backend.
  - Restored human-readable filenames with timestamp collision prevention.
  - Fixed cross-page filtering and restored missing Report Pack Builder options.
  - Achieved 100% green CI with 20/20 E2E pass rate across all modules.

### 11. Season Setup Automation
- **Rule**: Use the `season-setup` skill when configuring MDB files for a new swim season.
- **Architecture**:
    - **Configuration-Driven**: The system uses `config/venues.json` for pool parameters and `config/schedule.json` for meet-specific details (dates, home/away, host).
    - **Reusability**: Always pass the `year` argument to `generate_season.py` to target the correct schedule.
- **Critical Knowledge**:
...
    - **Lane Assignments**: Home teams are assigned to EVEN lanes (2, 4, 6...), and Away teams to ODD lanes (1, 3, 5...), matching the "4-2-6" and "3-5-1" priority rules.

    - **Date Format**: The `mdb_restorer` expects date fields to be **millisecond timestamps** (integers) in the JSON source. Providing ISO strings or other formats will lead to empty values or type mismatches in the final MDB.
    - **Entry-Open Date Logic**: 
        - For the **first meet** of a season, use `06/01/[PREVIOUS_YEAR]` to allow pulling times from the last full season.
        - For **subsequent meets**, use the date of the **first meet** of the current season (e.g., `05/30/2026`) to pull only current-season times.
    - **Schema Mapping**: When tables (like `Team`) are empty in the template, `SeasonTransformer` must use explicit `table_defs` to map columns correctly.
    - **Meet Defaults & Rule Deviations**: 
        - **Rule 12 Deviation**: While TVSL Rule 12 limits swimmers to 3 individual events, the historical league MDBs are configured to allow **4 total / 3 individual** entries. Automation MUST match this historical permissive default.
        - **Scoring**: Standard dual meet scoring is 5-3-2-1 for individuals and 10-6-0 for relays (Rule 19).
        - **Export Parity**: All EV3/HYV exports MUST use `7.0Gb` version strings and `\r\n` line endings for TeamUnify compatibility.
- **Action**: Check `.agent/skills/season-setup/SKILL.md` for execution and configuration details.

### 18. LSC Code Database Locations
- **Context**: Need to verify and modify team LSC codes (e.g., changing "CC" to "VS" for the Castlewood Barracudas).
- **Locations**:
  - **Team**: The primary location of a team's LSC code is the `Team_lsc` column in the `Team` table.
  - **Meet**: The LSC is stored in `Meet_lsc` and `Meet_hostlsc`.
  - **Records**: The LSC is stored in `Record_teamlsc` (in both `Records` and `RecordsbyEvent` tables).
  - **RecordTags**: The LSC is stored in `tag_lsc`.
- **References**: Other tables like `Athlete` and `Event` do not duplicate the LSC string. Athletes link to their team via `Team_no`.

### 19. Meet Validation Mappings & Exhibition Bypasses
- **Modular Design**: Business logic validations are decoupled from the gRPC transport layer. All integrity rules reside in `meet_validation.py`.
- **Exhibition Swims**: Exhibition swims are marked by a non-empty `Pre_exh` or `Fin_exh` column in the `entry` (or `relay` for teams) tables. These do NOT count against TVSL rules limits (max 3 individual / 4 total events).

### 20. Tauri Desktop App Architecture & WebView IPC Limits
- **Dynamic Port Discovery**: The frontend queries `get_backend_port` via Rust dynamically on every request. Caching this port in JS module scope is strictly forbidden to avoid dynamic startup race conditions.
- **Filesystem Bypass**: To download report packs/ZIPs in the desktop app, pass the URL to the custom Rust command `copy_file_from_storage(relative_path, dest_path)` which executes direct filesystem copies (`fs::copy`) natively. Large byte arrays must never be serialized as JSON arrays over WebView IPC.

### 21. Windows Dependency Packaging & Sidecar Stdin Monitoring
- **WeasyPrint Windows DLLs**: WeasyPrint requires Cairo, Pango, and GObject libraries on Windows. In GHA, install `mingw-w64-x86_64-pango` via MSYS2 `pacman` and copy all bin DLLs into `backend/src/mm_to_json/lib/` for PyInstaller packaging. Point WeasyPrint to them at startup using `WEASYPRINT_DLL_DIRECTORIES`.
- **GHA Matrix Checks**: The GHA workflow matrix uses `platform: windows` (NOT `windows-latest`). Using `windows-latest` in matrix platform checks will cause steps to be silently skipped.
- **Orphan Sidecar Process Prevention**: The Python sidecar supports stdin parent monitoring to prevent orphan background processes. Ensure `MONITOR_PARENT_PROCESS=true` is set when spawning the sidecar in Tauri, and do not enable it in headless/Docker environments to avoid immediate container exits.
- **Sidecar Package Validation**: Always run the compiled sidecar with `--check-weasyprint` on both macOS and Windows runners to validate library loading before building installers.




