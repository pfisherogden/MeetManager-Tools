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

3. **Commit with Issue Reference**:
   Commit changes using a descriptive message that includes the issue number:
   ```bash
   git add .
   git commit -m "Fix <description> (<bug-id>) - Issue #<number>"
   git push
   ```

4. **Update GitHub Issue**:
   Use the `add_issue_comment` tool (or `gh issue comment` if manual) to link the commit hash and provide a brief implementation summary:
   ```bash
   gh issue comment <number> --body "Fixed <description>. Commit: <hash>"
   ```
