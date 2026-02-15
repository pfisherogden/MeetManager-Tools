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

## Data & Mocking Best Practices
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