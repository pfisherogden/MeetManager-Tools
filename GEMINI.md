# Project Knowledge & Learnings

## Tech Stack
- **Framework**: React Native + Expo (Managed Workflow)
- **Web Platform**: Expo Web (Metro Bundler) + React Native Web
- **Deployment**:
  - **Docker**: Runs as a static site via Nginx (`docker run -p 8080:8080`).
  - **GitHub Pages**: Deployed via GitHub Actions to a subdirectory (`/MeetManager-Tools/`).

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

## Verification Workflow
1.  **Local Dev**: `npm start --web` (Fast feedback)
2.  **Docker Simulation**: `just up-mobile` (Verifies production build artifact)
3.  **Live Environment**: **ALWAYS** verify core journeys on the actual GitHub Pages deployment. Pathing issues often only manifest there.

## Local Development Prerequisites (macOS)
The backend uses **WeasyPrint** for PDF generation, which requires system-level libraries not included in `pip install`.

1.  **Install Homebrew Dependencies**:
    ```bash
    brew install glib pango cairo gdk-pixbuf libffi
    ```

2.  **Run Tests**:
    The `Justfile` recipe `test-backend-fast` automatically handles library paths:
    ```bash
    just test-backend-fast
    ```
## Reliability Standards

### 1. CI Stability (Zero Tolerance)
- **Rule**: NEVER push code that fails local linting or testing. CI failures on `main` are considered major regressions.
- **Mandatory Pre-Push**: Run `just lint` immediately before every `git push` to catch accidental formatting or whitespace issues.

### 2. 2-Cycle Verification
- **Rule**: For all major implementations, refactors, or bug fixes, you MUST run the relevant test suite (e.g., `just test-backend`) **2 times consecutively**. Both runs must pass 100% to consider the task complete. This catches most intermittent race conditions and flakiness while remaining efficient.

## CI/Test Strategy

### 1. Unified Test Fixtures
- **Problem**: Testing reports originally required `.mdb` files, which are gitignored and unavailable in CI or fresh local checkouts.
- **Solution**: 
  - Use committed JSON fixtures (`tests/fixtures/anonymized_meets/`) for all core reporting tests.
  - The `MmToJsonConverter` supports `table_data` directly, bypassing the need for an MDB parser in CI.
  - Tests in `test_reporting_advanced.py` are configured to find these fixtures in both local and Docker environments.

### 2. Type Checking (Mypy)
- **Rule**: All new logic in `extractor.py` and service layers must have explicit type signatures. CI runs `just lint-backend` which includes `mypy`.
