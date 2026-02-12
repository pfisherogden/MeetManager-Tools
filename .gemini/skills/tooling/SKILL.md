---
name: Tooling Preferences
description: Preferred tools for development and dependency management.
---
# Tooling Preferences

## General
- **Entry Point**: Always use `Justfile` (`just <command>`) for project operations to ensure consistency.
- **Docker**: The project requires a Docker-compatible engine (e.g., Docker Desktop, OrbStack, Colima). The user is responsible for ensuring the engine is running before executing build/up commands.

## Python (Backend)
- **Dependency Manager**: **uv** is the mandatory tool for Python.
- **Workflow**: 
  - Use `uv sync` for local environment setup.
  - Dependencies are managed in `backend/pyproject.toml`.
  - Avoid `requirements.txt` unless required by legacy deployment constraints.
- **Linting/Formatting**: Use `ruff` via `uv run ruff`.

## Node.js (Web Client)
- **Dependency Manager**: **npm** or **pnpm**.
- **Protobufs**: Use `ts-proto` for generating gRPC-web clients from definitions in the root `protos/` directory.

## Docker
- **Hermeticity**: Use multi-stage builds.
- **Context**: Maintain `.dockerignore` to exclude large artifacts (`node_modules`, `.next`, `venv`, etc.).
- **Proto Sync**: Handle protobuf generation within the Docker build process rather than copying files manually on the host.

## CI/CD Environment
- **Environment Parity**: CI environments (e.g., GitHub Actions) must explicitly install all mandatory tools (`uv`, `ruff`, `biome`) to mirror the local development environment.
- **Tool Installation**: Always verify that tools used in CI steps are either part of the project dependencies or explicitly installed (e.g., using `astral-sh/setup-uv` and `uv pip install ruff`).