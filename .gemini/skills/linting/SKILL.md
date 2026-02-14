---
name: Linting Standards
description: Enforcement of code style and quality checks for MeetManager-Tools. Use when formatting code or resolving linting errors.
---

# Linting Standards

## Python (Backend)
- **Use Ruff**: Apply Ruff for both linting and formatting.
- **Auto-Fix**: Run `just fix` to automatically resolve formatting and basic lint issues.
- **Prohibit Exceptions**: Avoid bare `except` blocks and unused imports.
- **Protect Stubs**: Exclude `.pyi` files from Ruff formatting to prevent conflicts with type stubs.

## TypeScript/React (Frontend)
- **Use Biome**: Apply Biome for linting and formatting the `web-client`.
- **Sync Version**: If CI reports schema mismatches, run `just fix` to execute `biome migrate`.
- **Ignore Strategy**: Leverage `.gitignore` for exclusions and explicitly ignore generated files in `web-client/lib/proto/`.

## Protocol Buffers
- **Use Buf**: Apply Buf for linting and formatting files in `protos/`. Use the `DEFAULT` category in `buf.yaml`.
- **Structure**: Maintain versioned directories (e.g., `v1/`).

## Verification
- **Local Check**: Run `just lint` before pushing.
- **Hermetic Check**: Use `just verify-ci` to catch environment-specific linting issues (e.g., binary mismatches).