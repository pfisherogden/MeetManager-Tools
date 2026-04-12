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

## Issue Updates & Progress Tracking
- **Preserve Context**: NEVER edit the original issue description (body) once it has been created by the user. This contains the primary requirements and should remain as the source of truth.
- **New Comments Only**: Always use the `add_issue_comment` tool to post status updates, research findings, and check-in notifications. 
- **Milestones**: Add a comment when:
    1. Research is finished and a strategy is chosen.
    2. A fix has been implemented and pushed to a branch.
    3. A PR has been created.
- **Completion Traceability**: Before closing an issue, add a final summary comment that explicitly lists the changes made and references the successful PR number and merge commit SHA. This provides a clear audit trail for the work.
