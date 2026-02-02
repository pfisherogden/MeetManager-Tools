---
name: Tooling Preferences
description: Preferred tools for development and dependency management.
---
# Tooling Preferences

## Docker First
- **Strategy**: Prefer using Docker and Docker Compose for running services, setups, and verifying builds.
- **Avoid**: Running services on bare metal if Docker containers are available.

## Python (Backend)
- **Manager**: Use **uv** for dependency management and package installation.
- **Usage**: `uv pip install ...`, `uv venv`, etc.
- **Config**: Maintain `pyproject.toml` for configuration.

## Node.js (Web Client)
- **Manager**: Use **npm** for node package management.
