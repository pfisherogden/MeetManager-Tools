---
name: Testing Standards
description: Guidelines for running and writing tests in MeetManager-Tools. Use when adding features, fixing bugs, or verifying system behavior.
---

# Testing Standards

## Core Principles
- **Mandatory Verification**: Every code change must be accompanied by tests.
- **Unified Entry Point**: Use `just test` for full suite execution.
- **Robustness**: Ensure gRPC server methods handle `request=None` gracefully.
- **Environment Consistency**: Prefer running tests in Docker (`just test-backend` or `docker-compose run ...`) over local execution to avoid OS-specific library issues (e.g., Cairo/Pango versions).

## Test Workflow
1. **Sync Dependencies**: Run `uv sync --all-packages --dev` (Backend) or `npm install` (Frontend).
2. **Generate Code**: Run `just codegen` if modifying `.proto` files.
3. **Execute Backend Tests**: Run `just test-backend` for `pytest`.
   - Focus on data parsing and report generation logic.
   - Verify PDF/PNG artifacts against snapshots in `backend/data/example_reports/`.
4. **Execute Frontend Tests**: Run `just test-frontend` for `Vitest`.
       - Focus on component rendering and Server Action interactions.
       - **Anti-Hang**: Always use `vitest run` (or `npm test -- --run`) in automated scripts to prevent the runner from entering watch mode and hanging the process.
5. **Local CI Check**: Run `just ci-local` to execute GitHub Actions locally using `act`. 
   - This MUST be done before creating or updating a PR to ensure all remote workflows pass.
   - **Cross-Platform**: The `Justfile` automatically detects the host environment. On Apple Silicon (M-series), it forces `--container-architecture linux/amd64` to ensure compatibility with standard Ubuntu-based action runners.

## Data & Mocking Best Practices
- **Sensitive Data False Positives**: Test logs containing variable names like `gender`, `team`, or `age` may trigger CodeQL's `py/clear-text-logging-sensitive-data` alert. Use the `# codeql [py/clear-text-logging-sensitive-data]` suppression comment on the logging line if the data is anonymized or intended for test verification.
- **Strict Case Sensitivity**: When mocking Pandas DataFrames or dictionaries for `MmToJsonConverter`, assume case-sensitive column access. Although the converter might normalize *loaded* data to lowercase, tests injecting raw data must match the expected internal keys exactly (e.g., use `convseed_time` not `ConvSeed_time`).
- **Fixture Consistency**: Ensure mock data matches the structure of real MDB exports. If the application logic relies on specific relationships (e.g., `Event_ptr` linking `Entry` to `Event`), manually verified mock data is crucial.

## Report Validation
- **Data Hydration**: Assert that all data fields (Meet Name, Team Filter, etc.) are correctly mapped from the request to the template data.
- **Edge Cases**: Explicitly test "NT" (No Time) entries, scratched swimmers, and complex relay structures (up to 4 swimmers + alternates).
   - **DOM Validation**: Use `BeautifulSoup` to parse generated HTML before it hits the PDF renderer. Assert:
       - Expected CSS classes (e.g., `.event-block`, `.col-lane`) are present.
       - No empty/invalid data fields.
       - The number of blocks matches the database query.
   - **Template Pitfalls**:
       - **Jinja2 Shadowing**: Never use the key `items` in a dictionary passed to Jinja2 templates (e.g., `group.items`). Jinja2 resolves `items` to the built-in `dict.items()` method, causing `UndefinedError` or unexpected behavior. Use `sections` or `entries` instead.
## Report Validation & Stability
- **Layout Stability**: WeasyPrint is highly unstable with 2-column layouts and `<table>` structures. Always prefer **DIV/Flexbox** layouts for report templates to ensure column synchronization and prevent `AttributeError` crashes in production.
- **Top-Alignment Rule**: When allowing text wrapping (e.g., for long names), use `align-items: flex-start` for entry rows. This ensures that columns remain horizontally aligned even if one field spans multiple lines.
- **Break Logic Optimization**: To maximize page density, avoid global `break-inside: avoid` on large blocks (e.g., `.event-block`). Instead, wrap only the **Header and First Heat** in a non-breaking container (`break-inside: avoid`) to ensure they stay together, while allowing subsequent heats to flow freely into the next column or page.
- **Renderer Logs**: Capture WeasyPrint or Playwright stdout/stderr to programmatically check for layout warnings like "Content box too small."

## Production Smoke Testing
- **Mandatory E2E Check**: After every production deployment, run a local smoke test suite (Playwright) against the live URL. This catches environment-specific failures (e.g., Cloud Run gRPC limits, GCS permissions) that CI might miss.
- **Non-Destructive Tests**: Production tests should focus on read-only actions (dashboard load, report generation, data fetching) or use dedicated test/sample datasets to avoid polluting live meet data.
- **Debug Endpoints**: Utilize unauthenticated test endpoints (e.g., `/api/test-bundle`) to verify large binary pipelines (ZIP generation/download) without requiring manual session credentials.

## Lessons Learned (Mobile Judge App)
- **UI/Test Sync**: When modifying UI text strings (e.g., simplifying "DQ Swimmer: Name" to "DQ: Name"), immediately grep for that string in `__tests__` or `test/` directories. UI copy changes often break strict text matchers in Jest.
- **Navigation Bounds**: When implementing list navigation (Next/Prev), always explicitly test the start (index 0) and end (index N-1) bounds to prevent out-of-range errors or visual glitches. Instead of faint disabled states, consider fully hiding (un-mounting) navigational arrows at the boundaries.
- **Mobile Touch Targets**: Ensure navigation elements (arrows, buttons) have sufficient padding (hit slop) for touch interaction, as verified by browser automation.
- **React Native Web Layouts**: Text wrapping behavior differs fundamentally between Native and Web. Ensure parent container views explicitly use `flexWrap: 'wrap'` when rendering flex-row lists on the Web to prevent text from overflowing or being truncated.