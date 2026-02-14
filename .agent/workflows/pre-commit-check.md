---
description: Ensure code quality and issue traceability before commit
---

To ensure high code quality and clear documentation, follow these steps before every commit that addresses a bug or feature:

1. **Lint and Format**:
// turbo
   Run the global fix command to automatically resolve formatting and basic linting issues:
   ```bash
   just fix
   ```
   *Note: This runs `fix-backend`, `fix-mm-to-json`, and `lint-frontend-fix`.*

2. **Verify All Checks**:
   Run the verification pipeline to ensure no regressions:
   ```bash
   just verify
   ```
   *Note: This runs all linters and the full test suite for both backend and frontend.*

3. **Record Evidence**:
   Before closing any issue, capture a visual recording of the fix in action using the browser subagent or manual methods. This recording MUST demonstrate the resolved bug across all relevant UI components.

4. **Commit with Issue Reference**:
   Commit changes using a descriptive message that includes the issue number:
   ```bash
   git add .
   git commit -m "Fix <description> (<bug-id>) - Issue #<number>"
   git push
   ```

5. **Update GitHub Issue**:
   Use the `add_issue_comment` tool to provide a brief implementation summary and refer to the local `walkthrough.md` for full verification evidence (since the GitHub API does not support direct video uploads):
   ```bash
   gh issue comment <number> --body "Fixed <description>. See walkthrough.md for verification evidence."
   gh issue close <number>
   ```
