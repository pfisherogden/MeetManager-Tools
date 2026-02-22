# Project Knowledge & Learnings

## Tech Stack
- **Framework**: React Native + Expo (Managed Workflow)
- **Web Platform**: Expo Web (Metro Bundler) + React Native Web
- **Deployment**:
  - **Docker**: Runs as a static site via Nginx (`docker run -p 8080:8080`).
  - **GitHub Pages**: Deployed via GitHub Actions to a subdirectory (`/MeetManager-Tools/`).

## Critical Configurations

### 1. Dynamic Base URL
- **Problem**: The app runs at root `/` in Docker but at `/MeetManager-Tools/` on GitHub Pages.
- **Solution**:
  - `app.json` was converted to `app.config.js`.
  - usage: `experiments: { baseUrl: process.env.APP_BASE_URL || "" }`
  - **Docker**: `APP_BASE_URL` is empty (default).
  - **GH Pages**: `APP_BASE_URL` is set to `/MeetManager-Tools` in `.github/workflows/deploy-mobile.yml`.

### 2. Native Assets on Web
- **Problem**: `Image` component with `tintColor` renders as a colored square on Web.
- **Solution**: Use `@expo/vector-icons` (e.g., `Ionicons`) for all UI icons. This ensures crisp, recolorable vector rendering across platforms.

### 3. Docker Build Environment
- **Problem**: Copying `node_modules` from macOS (M-series chips) to Linux/Alpine containers causes binary incompatibilities (e.g., `esbuild`).
- **Solution**: Always use `.dockerignore` to exclude `node_modules`. Let the container install its own dependencies.

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
## CI/Test Strategy

### 1. Unified Test Fixtures
- **Problem**: Testing reports originally required `.mdb` files, which are gitignored and unavailable in CI or fresh local checkouts.
- **Solution**: 
  - Use committed JSON fixtures (`tests/fixtures/anonymized_meets/`) for all core reporting tests.
  - The `MmToJsonConverter` supports `table_data` directly, bypassing the need for an MDB parser in CI.
  - Tests in `test_reporting_advanced.py` are configured to find these fixtures in both local and Docker environments.

### 2. Type Checking (Mypy)
- **Rule**: All new logic in `extractor.py` and service layers must have explicit type signatures. CI runs `just lint-backend` which includes `mypy`.
