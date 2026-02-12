---
name: Linting Standards
description: Enforcement of code style and quality checks.
---
# Linting Standards

## Python (Backend & Tools)
- **Ruff**: Use Ruff for both linting and formatting.
- **Automation**: Always run `just fix-backend` and `just fix-mm-to-json` before committing.
- **Rules**: Adhere to the configurations in `pyproject.toml`. Bare `except` and unused imports are strictly prohibited.

## TypeScript/React (Frontend)
- **Biome**: Use Biome for linting and formatting.
- **Configuration Compatibility**: Avoid the `files.ignore` key in `biome.json` as it causes schema errors in some CI environments. 
- **Exclusions**: Use the project's `.gitignore` to exclude directories from Biome scanning. Ensure `vcs.useIgnoreFile` is enabled in `biome.json`.
- **Generated Code**: Always ignore generated gRPC/Proto files (e.g., `web-client/lib/proto/`) to avoid duplicate declaration errors.

## CI Integration
- **Verification**: Linting MUST pass in CI. Locally, verify with `just lint` or the hermetic `just verify-ci` to catch architecture-specific issues (like Biome binary mismatches).