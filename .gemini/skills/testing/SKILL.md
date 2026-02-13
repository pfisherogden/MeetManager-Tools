---
name: Testing Standards
description: Guidelines for running and writing tests in MeetManager-Tools. Use when adding features, fixing bugs, or verifying system behavior.
---

# Testing Standards

## Core Principles
- **Mandatory Verification**: Every code change must be accompanied by tests.
- **Unified Entry Point**: Use `just test` for full suite execution.
- **Robustness**: Ensure gRPC server methods handle `request=None` gracefully.

## Test Workflow
1. **Sync Dependencies**: Run `uv sync --all-packages --dev` (Backend) or `npm install` (Frontend).
2. **Generate Code**: Run `just codegen` if modifying `.proto` files.
3. **Execute Backend Tests**: Run `just test-backend` for `pytest`.
   - Focus on data parsing and report generation logic.
   - Verify PDF/PNG artifacts against snapshots in `backend/data/example_reports/`.
4. **Execute Frontend Tests**: Run `just test-frontend` for `Vitest`.
   - Focus on component rendering and Server Action interactions.

## Design Patterns
- **Unit over Integration**: Prefer testing logic in isolation before full system tests.
- **Snapshots**: Use file-based snapshots for visual reports to ensure data integrity across transformations.