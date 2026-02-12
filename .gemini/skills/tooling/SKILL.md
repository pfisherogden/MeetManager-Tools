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
- **Workspace Sync**: In the root directory, always use `uv sync --all-packages --dev` to ensure all workspace members have their dependencies installed.

## Frontend & Codegen
- **Node.js**: Use Node v20 for the `web-client`. 
- **CI Codegen**: GitHub Actions MUST run `npm install` in the `web-client` directory before `just codegen`. This is critical because `grpc-tools` requires native binaries that only exist after a fresh install.

## Docker & Hermeticity
- **Context Bloat**: Maintain `.dockerignore` to exclude host-side artifacts (`node_modules`, `.venv`, `.jdk`). This prevents build hangs and architecture mismatches.
- **Clean Room**: Use `just verify-ci` to validate changes in a Docker container mirroring the CI environment. This is the only way to catch architecture-specific binary issues locally.