---
name: Testing Standards
description: Guidelines for running and writing tests in this project.
---
# Testing Standards

## Principles
- **Mandatory Verification**: Every feature or fix must include tests.
- **Unified Entry Point**: Use `just test` to run all project tests.

## Preparation (CI & Local)
- **Dependency Sync**: Before running tests, ensure all dependencies are synced. In CI, use `uv sync --all-packages --dev`.
- **Code Generation**: Tests that depend on generated code (e.g., gRPC protos) must run `just codegen` as a prerequisite.

## Backend (Python)
- **Framework**: `pytest`.
- **Logic Tests**: Cover data parsing and gRPC service logic.
- **Report Verification**: Tests should verify that generated PDF/PNG reports match expected data snapshots.
- **Command**: `just test-backend` (runs `pytest` in Docker or local `uv` environment).

## Frontend (web-client)
- **Framework**: `Vitest`.
- **Component Tests**: Ensure UI components render correctly and handle interactions.
- **End-to-End**: Use Playwright or similar for critical user flows (optional but recommended for complex workflows).
- **Command**: `just test-frontend` (runs `npm test`).

## Artifacts
- **Snapshots**: Maintain snapshots for verification reports in `backend/data/example_reports/`.