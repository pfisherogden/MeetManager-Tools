---
name: github-workflow
description: Best practices for GitHub flows in MeetManager-Tools
---

# GitHub Workflow Guidelines

## Project Workflow (Mandatory)

### 1. GitHub Issues
- **Requirement**: Every task MUST have an associated GitHub Issue. If one doesn't exist, create it before starting work.
- **Updates**: Periodically update the issue with progress. Use new comments to preserve history.
- **Closing**: Only close the issue AFTER the Pull Request has been merged into `main` and all CI/CD checks have passed.

### 2. Communication
- **Google Chat**: For every significant milestone (e.g., finishing research, opening a PR, merging to main), update the user in the `pfo-gemcli` Google Chat space.
- **Format**: Summarize accomplishments and link to relevant PRs or issues.

## Mandatory Quality Checks
**NEVER** push code without running the following checks locally:
1. **Linting**: Run `just fix` (to auto-fix) and `just lint` (to verify zero remaining errors).
2. **Type Checking**: Run `just type-check-backend`. All new logic MUST have explicit type signatures.
3. **Pre-Push Verification**: Run `just pre-push` to execute all linters, type checks, and fast tests before any `git push`.
4. **Execution Verification**: Run `just pre-commit` to execute all linters, tests, AND production builds across the project. This is the **Source of Truth** for full verification.
5. **Testing**: Use committed JSON fixtures (`tests/fixtures/anonymized_meets/`) for reporting tests to ensure CI stability.

> [!IMPORTANT]
> **Zero Tolerance for CI Failures**: Merging code that breaks CI linting, type-checking, or tests is considered a failure. Always verify everything passes 100% locally before pushing.

## Reliability Standards (Mandatory)
- **2-Cycle Verification**: For all major implementations, refactors, or bug fixes, you MUST run the relevant test suite (e.g., `just test-backend`) **2 times consecutively**. Both runs must pass 100% to consider the task complete. This catches most intermittent race conditions and flakiness while remaining efficient.

## Branching
- Base all new features on `main`.
- Use descriptive branch names like `feat/feature-name` or `fix/bug-name`.

## Issue Updates
- **Add Comments**: When updating a GitHub issue with progress or new information, always add a **new comment**.
- **Do Not Edit**: Do not rewrite or edit previous status updates unless correcting a factual error (e.g., a typo). This ensures the history of the work is preserved.

## Context Optimization (Mandatory)
To maintain context efficiency and prevent Out-Of-Memory (OOM) crashes in large projects:
1. **Surgical Reads**: NEVER read large source files (e.g., >500 lines) in their entirety. ALWAYS use `start_line` and `end_line` parameters with `read_file`.
2. **Efficient Discovery**: Prioritize `grep_search` with `context` to identify specific logic points before reading files.
3. **Precise Edits**: Provide significant context in `old_string` when using `replace` to ensure unambiguous targeting.
4. **Lean History**: Keep conversation history high-signal. Avoid conversational filler and repetitive tool-use narration.
