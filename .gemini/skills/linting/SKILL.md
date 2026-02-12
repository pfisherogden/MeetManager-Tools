---
name: Linting Standards
description: Enforcement of code style and quality checks.
---
# Linting Standards

**Requirement**: All code must pass linting and formatting checks before merging.

## Backend (Python)
- **Tool**: Ruff (Linter & Formatter)
- **Rules**: Defined in `backend/pyproject.toml`.
- **Command**: `just lint-backend` (runs `uv run ruff check .` and `uv run ruff format --check .`).
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
    - `lint/style/useNodejsImportProtocol`: Use `node:` protocol for built-in Node.js modules (e.g., `import path from 'node:path'`).
    - `assist/source/organizeImports`: Ensures consistent sorting of import and export statements.
    - `lint/complexity/useOptionalChain`: Promotes using optional chaining (`?.`) for safer property access.
    - **Tailwind CSS Directives**: Correct parsing of `@apply`, `@screen`, `@tailwind`, etc., in CSS files.


## Global
- **Command**: `just lint` should run all linting tasks across the project.
- **CI/CD Integration**: All linting commands must be integrated into the CI pipeline with verified tool installation steps.