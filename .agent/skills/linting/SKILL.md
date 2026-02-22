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
- **Avoid sys.path hacks**: Do not use `sys.path.insert` or `sys.path.append` for local module imports. This triggers `E402` (imports not at top of file) and interferes with `isort` sorting. Instead:
    - Set `PYTHONPATH` in the execution environment (e.g., Dockerfile `ENV` or `Justfile` recipe).
    - Use absolute imports relative to the package root.
    - If `E402` is unavoidable in a standalone script, prefer sorting imports and using `# noqa: E402` only as a last resort.

## TypeScript/React (Frontend)
- **Use Biome**: Apply Biome for linting and formatting the `web-client`.
- **Sync Version**: If CI reports schema mismatches, run `just fix` to execute `biome migrate`.
- **Ignore Strategy**: Leverage `.gitignore` for exclusions and explicitly ignore generated files in `web-client/lib/proto/`.

## Protocol Buffers
- **Use Buf**: Apply Buf for linting and formatting files in `protos/`. 
- **Config**: Use the `STANDARD` category in `buf.yaml` (avoid the deprecated `DEFAULT`). This requires `version: v2` and `buf` CLI version **1.42.0** or higher.
- **Structure**: Maintain versioned directories (e.g., `v1/`).

## Verification
- **Local Check**: Run `just lint` before pushing.
- **Hermetic Check**: Use `just verify-ci` to catch environment-specific linting issues (e.g., binary mismatches).
