---
name: github-workflow
description: Best practices for GitHub flows in MeetManager-Tools
---

# GitHub Workflow Guidelines

## Mandatory Quality Checks
**NEVER** commit code without running the following checks locally:
1. **Linting**: Run `just fix` (to auto-fix) and `just lint` (to verify zero remaining errors).
2. **Type Checking**: Run `just lint-backend` which includes `mypy`. All new logic MUST have explicit type signatures.
3. **Execution Verification**: Run `just pre-commit` to execute all linters, tests, AND production builds across the project. This is the **Source of Truth**.
4. **Testing**: Use committed JSON fixtures (`tests/fixtures/anonymized_meets/`) for reporting tests to ensure CI stability.

> [!IMPORTANT]
> **Zero Tolerance for CI Failures**: Merging code that breaks CI linting, type-checking, or tests is considered a failure. Always verify everything passes 100% locally before pushing.

## Reliability Standards (Mandatory)
- **5-Cycle Verification**: For all major implementations, refactors, or bug fixes, you MUST run the relevant test suite (e.g., `just test-backend`) **5 times consecutively**. All 5 runs must pass 100% to consider the task complete.

## Branching
- Base all new features on `main`.
- Use descriptive branch names like `feat/feature-name` or `fix/bug-name`.

## Issue Updates
- **Add Comments**: When updating a GitHub issue with progress or new information, always add a **new comment**.
- **Do Not Edit**: Do not rewrite or edit previous status updates unless correcting a factual error (e.g., a typo). This ensures the history of the work is preserved.
