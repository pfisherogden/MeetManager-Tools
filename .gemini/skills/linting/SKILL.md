---
name: Linting Standards
description: Enforcement of code style and quality checks.
---
# Linting Standards

**Requirement**: All code must pass linting and formatting checks before merging.

## Automation First
- **Auto-Fix**: Always run `just lint` (or specific `just fix-*` commands) to automatically resolve safe linting issues and apply formatting before committing code.
- **Mandatory Formatting**: All Python code must be formatted using `ruff format`.

## Backend (Python)
- **Tool**: Ruff (Linter & Formatter)
- **Rules**: Defined in `backend/pyproject.toml`.
- **Commands**:
    - `just lint-backend`: Checks for issues without modifying code (used in CI).
    - `just fix-backend`: Automatically fixes safe issues and applies formatting (preferred for local development).
- **CI Verification**: Ensure `ruff` is explicitly installed in the CI environment to avoid execution failures.

## Frontend (Typescript)
- **Tool**: Biome (Linter & Formatter)
- **Configuration**: `web-client/biome.json` configured for TypeScript and Tailwind CSS directives.
- **Commands**:
    - `just lint-frontend` (runs `cd web-client && npm run lint`): Checks for linting and formatting issues.
    - `just lint-frontend-fix` (runs `cd web-client && npm run format && npm run lint:fix`): Applies safe fixes and formatting.
    - `just format-frontend` (runs `cd web-client && npm run format`): Applies formatting.
    - `just format-frontend-check` (runs `cd web-client && npm run format:check`): Checks only for formatting issues.
- **Common Issues Addressed**:
    - `lint/suspicious/noExplicitAny`: Avoid explicit `any` types for improved type safety.
    - `lint/style/useNodejsImportProtocol`: Use `node:` protocol for built-in Node.js modules.
    - `assist/source/organizeImports`: Ensures consistent sorting of imports.

## Global
- **Command**: `just lint` runs all linting and **fixing** tasks across the project. Use this as your primary verification step.
- **CI/CD Integration**: CI pipelines run `just lint-backend` and `just lint-frontend` to verify code quality without modifying files.