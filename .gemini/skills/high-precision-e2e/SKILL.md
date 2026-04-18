# Skill: High-Precision E2E Testing for Dual-App Workflows

Use this skill when developing or debugging Playwright tests that span both the main MeetManager-Tools webapp and the mobile-judge-app SPA.

## **Core Principle**
Isolate test state using unique User IDs and separate browser contexts to ensure reliable results in shared CI environments.

## **Step 1: Environment Preparation**
1.  **Unique User ID**: Always generate a unique `userId` per test run (e.g., `e2e-dq-${Math.random()}`).
2.  **Isolated Contexts**: Create separate `browserContext` instances for each role (Admin, Judge, Volunteer). This ensures cookies and local storage do not leak between roles.
    ```typescript
    const judgeContext = await browser.newContext({ viewport: { width: 375, height: 667 } });
    const adminContext = await browser.newContext();
    ```

## **Step 2: Database Isolation**
Ensure all requests pass the `x-user-id` header to the backend.
1.  **Headers**: Use `page.setExtraHTTPHeaders({ 'x-user-id': userId })`.
2.  **Cookies**: Add a fallback cookie `await context.addCookies([{ name: 'x-user-id', value: userId, ... }])`.

## **Step 3: Real-World Link Flow**
Do not hardcode Judge App URLs. Mirror the real user experience:
1.  **Admin Page**: Go to `/admin` and click "Publish to Judge App".
2.  **Extract URL**: Locate the short-link in the success dialog and extract the text.
3.  **Local Mapping**: In local dev/CI, the published URL might point to port `:3000`. Use regex to remap it to the mobile app port (usually `:8080`).
    ```typescript
    const localUrl = publishedUrl.replace(/localhost:3000/i, "localhost:8080");
    ```

## **Step 4: Data Sync Verification**
Verify that data flows from the Judge App to the backend and back to the Volunteer dashboard.
1.  **Submission**: Submit a DQ in the Judge App.
2.  **Polling**: On the Volunteer page, wait for the live update (up to 15s).
3.  **Granular Verification**: For relays, specifically check that individual swimmer names are present in the DQ list, not just the team name.

## **Red Flags**
- **Sequential Tests**: Sharing the same `userId` between tests causes non-deterministic failures.
- **Race Conditions**: Polling loops in the UI can lead to `element not found`. Use `toBeVisible({ timeout: 15000 })`.
- **Docker Throttling**: Heavy renders (150s+) will trigger Playwright's default timeout. Always bump `test.setTimeout` for reporting journeys.
