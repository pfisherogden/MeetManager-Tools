---
name: Justfile Management
description: Best practices for writing and maintaining Justfiles in MeetManager-Tools. Use when adding or modifying project automation recipes.
---

# Justfile Management

## Core Principles
- **Source of Truth**: Use the `pre-commit` target to run the absolute full verification suite before pushing.
- **Manage Dependencies**: Use recipe dependencies (e.g., `test: codegen`) to ensure correct execution order.
- **Ensure Consistency**: Design recipes to behave identically in both local and Docker environments.

## Recipe Patterns
- **Verification**: The `verify` target should include linting, tests, AND production builds (`build-frontend`, `build-mobile`) to catch build-time errors (e.g., Tailwind CSS token mismatches).
- **Codegen**: Ensure all recipes dependent on generated code explicitly depend on `codegen`.
- **Cleanup**: Provide a `clean` recipe to purge caches and temporary artifacts.

## Best Practices
- **Quiet Execution**: Use `@` to suppress command echoing for cleaner output.
- **Shell Consistency**: Always set `set shell := ["bash", "-c"]` at the top of the Justfile.
- **Fail Fast**: Chain logical steps with `&&`.
- **PYTHONPATH Pattern**: For backend tests and scripts, explicitly set `PYTHONPATH=src` (or similar) within the recipe. This ensures imports resolve correctly even when the code is not installed as a package in the environment.
- **Scoped Variables**: Prefix commands with necessary environment variables rather than relying on global state.

