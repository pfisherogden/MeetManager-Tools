---
name: Justfile Management
description: Best practices for writing and maintaining Justfiles in MeetManager-Tools. Use when adding or modifying project automation recipes.
---

# Justfile Management

## Core Principles
- **Separate Checks from Fixes**: Maintain `lint` (read-only) and `fix` (modifying) recipes.
- **Manage Dependencies**: Use recipe dependencies (e.g., `test: codegen`) to ensure correct execution order.
- **Ensure Consistency**: Design recipes to behave identically in both local and Docker environments.

## Recipe Patterns
- **Linting**: Group all read-only checks under a `lint` recipe.
- **Fixing**: Group all modifying actions (formatting, migration) under a `fix` recipe.
- **Codegen**: Ensure all recipes dependent on generated code explicitly depend on `codegen`.
- **Cleanup**: Provide a `clean` recipe to purge caches and temporary artifacts.

## Best Practices
- **Quiet Execution**: Use `@` to suppress command echoing for cleaner output.
- **Shell Consistency**: Always set `set shell := ["bash", "-c"]` at the top of the Justfile.
- **Fail Fast**: Chain logical steps with `&&`.
- **Scoped Variables**: Prefix commands with necessary environment variables rather than relying on global state.

