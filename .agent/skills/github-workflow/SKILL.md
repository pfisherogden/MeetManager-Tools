---
name: github-workflow
description: Best practices for GitHub flows in MeetManager-Tools
---

# GitHub Workflow Guidelines

## Mandatory Quality Checks
**NEVER** commit code without running the following checks locally:
1. **Linting**: Run `just fix` (to auto-fix) and `just lint` (to verify zero remaining errors).
2. **Type Checking**: Run `just lint-backend` which includes `mypy`. All new logic MUST have explicit type signatures.
3. **Testing**: Run all relevant tests (e.g., `just test-backend-fast` or via Docker). Use committed JSON fixtures (`tests/fixtures/anonymized_meets/`) for reporting tests.
4. **Local Verification**: Run `just verify` to execute all linters and tests across the project.

> [!IMPORTANT]
> **Zero Tolerance for CI Failures**: Merging code that breaks CI linting, type-checking, or tests is considered a failure. Always verify everything passes 100% locally before pushing.

## Branching
- Base all new features on `main`.
- Use descriptive branch names like `feat/feature-name` or `fix/bug-name`.
