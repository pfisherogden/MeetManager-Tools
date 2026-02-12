---
name: Tooling Preferences
description: Preferred tools for development and dependency management.
---
# Tooling Preferences

## Task Runner
- **Just**: Use `just` for all project-level commands. Never run complex shell strings manually if a recipe exists.
- **CI/CD**: Ensure `extractions/setup-just` is present in GitHub Actions to avoid 'command not found' errors.

## Python Management
- **UV**: Use `uv` for dependency management and virtual environments.
- **Workspace Sync**: In the root directory, always use `uv sync --all-packages --dev` to ensure all workspace members (backend, tools) have their dependencies (like `pytest`) installed.

## Frontend & Codegen
- **Node.js**: Use Node v20 for the `web-client`. 
- **CI Codegen**: GitHub Actions MUST run `npm install` in the `web-client` directory before `just codegen` to ensure `grpc-tools` binaries are available.

## Docker & Hermeticity
- **Context Bloat**: Always maintain `.dockerignore` to exclude host-side artifacts (`node_modules`, `.venv`, `.next`, `.jdk`). Sending these to the daemon causes build hangs.
- **Clean Room**: Use `just verify-ci` to validate changes in a Docker container that mirrors the CI environment before pushing.