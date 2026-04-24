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

## Reliability Standards (Mandatory)
- **2-Cycle Verification**: For all major implementations, refactors, or bug fixes, you MUST run the relevant test suite (e.g., `just test-backend` or `npm run test-e2e`) **2 times consecutively**. All 2 runs must pass 100% to consider the task complete. This catches flakiness and race conditions efficiently.
- **E2E Shard Isolation**: Playwright shards tests at the **test case** level. In a sharded CI environment, every individual test case MUST be fully self-contained. This includes ensuring its own dataset is active (e.g., via `ensureDataset`) at the start of the test to prevent data-race conditions where one worker's activation is overwritten by another's.
- **Stateless Sharing (Next.js)**: In CI/E2E environments, data shared between API routes and Server Actions MUST use file-based mocks (with `fsync` and retries) instead of in-memory maps, as they run in separate worker processes.
- **Volume Permissions**: When using Docker volumes in GHA, ensure the mount point on the host is world-writable (`chmod 777`) before starting services to prevent `EACCES` errors in the container.

## CI Optimization & Browser Testing
- **E2E Sharding**: Use Playwright sharding (e.g., 32-way) in CI to reduce total runtime. Verify shards pass independently.
- **User Gesture Compliance**: Headless browsers often block actions like `window.open` if not triggered by a direct user gesture. When testing features that open new tabs after an async server action, refactor the code to open a blank tab *synchronously* in the click handler and populate its content once the promise resolves.

## Robust Playwright Selectors
- **Ambiguity**: If multiple buttons have the same name (e.g., "Apply to Builder" in a list), use `data-testid` or scoped locators: `page.locator("div", { has: page.getByText("Specific Item") }).getByRole("button")`.
- **Standardized UI Selectors**: Use `data-testid` exclusively for critical E2E interactions (e.g., `data-testid="generate-report-button"`) to prevent "element not found" errors when button text or roles are changed during design refactors.
- **Mobile Interaction**: In mobile Safari emulation, pointer events are frequently intercepted by overlapping elements. Use `page.evaluate(() => el.click())` for critical buttons to ensure interaction stability.
- **Viewport Height**: Use a tall viewport (e.g., 1200px) in mobile emulation to prevent the soft keyboard from pushing UI elements out of view.
- **Inputs**: For verifying text inside an `<input>` or `<textarea>`, prefer `getByDisplayValue()` over `getByText()`, as the latter may not find the value of a form field.
- **Spinners**: To check for loading states, use `toBeVisible()` on the spinner icon (e.g., `.animate-spin`) or `toBeAttached()` if the transition is very fast.

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
   - **Renderer Logs**: Capture WeasyPrint or Playwright stdout/stderr to programmatically check for layout warnings like "Content box too small."
   
   ## Design Patterns
   
- **Unit over Integration**: Prefer testing logic in isolation before full system tests.
- **Snapshots**: Use file-based snapshots for visual reports to ensure data integrity across transformations.

## Live Environment Verification
- **Pathing Issues**: GitHub Pages hosts sites in a subdirectory (e.g., `/Repo-Name/`). Always verify the app on the deployed URL to catch pathing regressions that don't appear in Docker root deployments.
- **Asset Loading**: Check the browser console on the live site for 404s on JS chunks or assets, which often indicate `publicPath` or `baseUrl` configuration errors.
- **Service Workers**: If implementing PWAs, verify service worker registration scope matches the subdirectory.

## Lessons Learned (Mobile Judge App)
- **UI/Test Sync**: When modifying UI text strings (e.g., simplifying "DQ Swimmer: Name" to "DQ: Name"), immediately grep for that string in `__tests__` or `test/` directories. UI copy changes often break strict text matchers in Jest.
- **Navigation Bounds**: When implementing list navigation (Next/Prev), always explicitly test the start (index 0) and end (index N-1) bounds to prevent out-of-range errors or visual glitches. Instead of faint disabled states, consider fully hiding (un-mounting) navigational arrows at the boundaries.
- **Mobile Touch Targets**: Ensure navigation elements (arrows, buttons) have sufficient padding (hit slop) for touch interaction, as verified by browser automation.
- **React Native Web Layouts**: Text wrapping behavior differs fundamentally between Native and Web. Ensure parent container views explicitly use `flexWrap: 'wrap'` when rendering flex-row lists on the Web to prevent text from overflowing or being truncated.