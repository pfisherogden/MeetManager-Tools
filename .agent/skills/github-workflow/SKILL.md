---
name: github-workflow
description: Best practices for GitHub flows in MeetManager-Tools
---

# GitHub Workflow Guidelines

## Mandatory Quality Checks
**NEVER** commit code without running the following checks:
1. **Linting**: Run `just fix` (to auto-fix) and `just lint` (to verify zero remaining errors).
2. **Testing**: Run all relevant tests (e.g., `just test-backend-fast` or via Docker).
3. **Draft PRs**: If you are unsure, push to a branch and wait for CI to pass before marking as ready for review.

> [!IMPORTANT]
> **Zero Tolerance for Linting Errors**: Merging code that breaks CI linting is considered a failure. Always verify `just lint` passes 100% locally.

## Branching
- Base all new features on `main`.
- Use descriptive branch names like `feat/feature-name` or `fix/bug-name`.
