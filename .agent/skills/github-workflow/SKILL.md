---
name: github-workflow
description: Mandatory practices for GitHub workflows and session continuity in MeetManager-Tools
---

# GitHub Workflow & Agent Resilience

## Project Workflow (Mandatory Phases)

### Phase 1: Research & Strategy
- **Issue Check**: Search for an existing GitHub issue. Create one if it doesn't exist.
- **Strategy Proposal**: Before implementing, provide a strategy using this template:
  - **Summary**: What are we doing?
  - **Rationale**: Why this way?
  - **Approach**: Step-by-step technical plan.
  - **Security**: Secret/PII safety check.
  - **Testing**: How will we verify success?

### Phase 3: Surgical Implementation
- **Local Verification (Mandatory Pre-Push)**: Before running `git push`, you MUST execute the following to catch whitespace, linting, and formatting errors:
  - `just fix`: This will automatically resolve most formatting issues across the project.
  - `just lint`: Verify that no manual fixes are required.
  - `just test-backend-fast` and `cd web-client && npm test`: Ensure core logic is still passing.
- **Separate Branches**: NEVER push to `main`. Use `feat/*` or `fix/*`.

- **Code Preservation**: Preserve all existing comments, whitespace, and formatting in `old_string`. Do not refactor unrelated code.
- **Documentation**: All new logic MUST include explicit type hints and Google-style docstrings.
- **Dependency Management**: Use `uv` (Python) or `npm` (JS) and run lockfile updates immediately after any change.

### Phase 3: Verification & Closure
- **Local Verification**: 100% pass on `just lint`, `just type-check-backend`, and `just test-backend-fast`.
- **5-Cycle Rule**: For major refactors, run the relevant test suite **5 times consecutively** to catch flakiness.
- **CI/CD Pass**: Merge ONLY after all GitHub Actions are green on the PR.
- **Issue Closure**: Only close after the PR is merged and CI/CD passes on the `main` branch.

## Session Continuity & Resilience
To ensure continuity across crashes or session timeouts:
1. **GitHub Issue Updates**: Post a comment with **"Current Progress"** and **"Planned Next Steps"** every 3-5 turns or at major milestones.
2. **Chat Communication**: Post progress updates to the `pfo-gemcli` Google Chat space.
   - **Work Started**: Notify when beginning a task or major phase.
   - **Work Completed**: **Mandatory** - Notify when work is finished, merged, or deployed. **Start a new thread for completions** to ensure unread notifications for the user.
   - **Frequency**: Every 15-20 minutes or at major milestones.
3. **Context Precedence**: `GEMINI.md` and this skill take absolute precedence over general defaults.

## Surgical Read & Edit Rules
1. **No Bulk Reads**: NEVER read files >500 lines in full. Use `start_line` and `end_line`.
2. **Contextual Grep**: Use `grep_search` with `context` to find logic before reading.
3. **Precise Replace**: Provide enough context in `old_string` to ensure unambiguous targeting.
