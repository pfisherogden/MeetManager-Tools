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
- **Code Preservation**: Preserve all existing comments and formatting. Do not refactor unrelated code.
- **Documentation**: All new functions/classes MUST include type hints and Google-style docstrings.
- **Dependency Protocol**: Use `uv` (Python) or `npm` (JS) and update lockfiles immediately after adding packages.

### Phase 4: Verification & Closure
- **Local Verification**: 100% pass on linting, type-checking, and tests before pushing.
- **CI/CD Monitoring**: **Mandatory** - After submitting a PR, you MUST monitor the GitHub Action checks using `gh pr checks`. Do not consider the task finished or close the issue until all checks are green and the PR is successfully merged.
- **CI/CD Pass**: PR merging is ONLY permitted after all GitHub Actions are green.
- **Communication**: Provide **periodic** progress updates in the `pfo-gemcli` Google Chat space.
  - **Work Started**: Post a message when beginning a task or after a major design phase.
  - **Work Completed**: **Mandatory** - Post a summary message when a task is finished, PR is merged, or a deployment is verified. **Always start a new thread for completions** to ensure they appear as new/unread notifications.
  - **Frequency**: Update the chat every 15-20 minutes or at major milestones.
- **Persistence**: Periodically update the GitHub issue with **Next Steps** to ensure session continuity.

### Technical Integrity & Safety
- **Mandatory Pre-Commit**: ALWAYS run `just fix` and `just lint` before pushing to `main`. This catches trailing whitespace, formatting, and Mypy issues that break CI.
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

## Recent Learnings & Persistent Decisions
- **2026-04-17**: Implemented **Asynchronous Job Pattern** for report generation to resolve 504 Gateway Timeouts. The backend now returns a `job_id` and processes in a background thread while the frontend polls for progress. (Issue #350).
- **2026-04-17**: Switched to **GCS Signed URLs** for large bundle delivery, offloading heavy bandwidth and memory usage from the backend services. (Issue #351).
- **2026-04-17**: Optimized WeasyPrint rendering by 2x using **CSS Table Layout** (`display: table`) instead of Flexbox and disabling font subsetting via `optimize_size=('images',)`. This also resolved header and relay alignment regressions. (Issue #349).
- **2026-04-17**: Found that in-memory job state is lost during Cloud Run rotations; **Firestore** is mandatory for all background task tracking.
- **2026-04-17**: Identified that 2-column layouts have exactly **255pt** of width per column (letter page). All fixed column widths must sum to this value to prevent gutter overlap.
- **2026-04-18**: **CI Stability & E2E Reliability**:
  - **File-based Mocks**: Stateless API routes and Server Actions in Next.js do not share in-memory state. A file-based mock (using `fsync` and retries) is mandatory for consistent data sharing in CI/E2E environments.
  - **Volume Permissions**: Docker volumes mounted from host to container in GHA often have permission mismatches. Ensure the mount point (e.g. `./tmp`) is world-writable (`chmod 777`) on the host before starting services.
  - **Dynamic Routing**: E2E tests must support subdirectory paths (e.g. `/MeetManager-Tools/`) to match production/GitHub Pages environments. Use relative origin remapping instead of stripping the entire path.
  - **Stable IDs**: Always use stable business-logic-based IDs (e.g. `dq-{event}-{swimmer}-{leg}`) for idempotency and to prevent duplicates during sync/edit operations.
- **2026-04-19**: **Mobile Safari E2E Robustness**:
  - **Pointer Interception**: Mobile Safari emulation often suffers from pointer-event interception by overlapping or transparent elements. Use `page.evaluate(() => el.click())` for critical buttons to ensure interaction stability.
  - **Viewport Awareness**: Increase viewport height (e.g. to 1200px) in mobile emulation to prevent the soft keyboard or narrow layouts from pushing critical buttons out of view.
- **2026-04-23**: **High-Concurrency E2E Sharding & UI Stability**:
  - **Shard Isolation**: Playwright shards tests at the **test case** level. Every test case MUST be fully self-contained, ensuring its own dataset is active (e.g., via `ensureDataset`) to prevent race conditions or missing data in high-shard (32+) environments.
  - **User Gesture Compliance**: Browsers (especially in headless CI) block `window.open` if not triggered by a direct user gesture. Synchronous server actions are rare; prefer opening a blank tab *synchronously* in the click handler and populating its content once the promise resolves.
  - **Server Action Signature Safety**: Functions with 5+ positional arguments are highly prone to ordering bugs during refactors. Always use named objects/interfaces for complex server actions to prevent "Ghost Argument" bugs.
  - **Component/Test Sync**: When refactoring component signatures (e.g., changing props to state), unit tests (Vitest) must be updated immediately. Ensure mocks for `@/app/actions` match the actual implementation's exports and return types.
  - **Standardized UI Selectors**: Use `data-testid` exclusively for E2E interactions to prevent "element not found" errors when button text or roles change (e.g., "Download" vs "Generate").


### 11. Season Setup Automation
- **Rule**: Use the `season-setup` skill when configuring MDB files for a new swim season.
- **Action**: Check `.agent/skills/season-setup/SKILL.md` for execution and configuration details.
