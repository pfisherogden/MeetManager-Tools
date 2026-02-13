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
- **Buf**: Use Buf for Protocol Buffer management.

## Docker & Parity
- **Optimize Context**: Maintain `.dockerignore` to exclude `node_modules`, `.venv`, and other host-side artifacts.
- **Build Caching**: Design Dockerfiles to cache dependencies separately from source code by copying `package.json` or `pyproject.toml` first.
- **Verify Locally**: Use `just verify-ci` to run the full verification pipeline in a container that mirrors the CI environment.