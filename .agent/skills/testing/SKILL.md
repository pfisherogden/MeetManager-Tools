# Skill: High-Precision E2E Stabilization

This skill provides expert guidance for hardening Playwright E2E tests in the MMTools project, specifically targeting race conditions, state leakage, and hydration hangs in the integrated Judge App.

## 🎯 Core Principles

1.  **Zero Leakage**: Every test journey MUST start with a clean slate.
2.  **Pre-emptive Listening**: Listeners for network responses MUST be initialized BEFORE the action that triggers them.
3.  **Monolith Readiness**: Tests MUST account for the Judge App being served via Next.js rewrites in the monolith.

## 🛠 Hardening Patterns

### 1. Explicit State Reset
Never assume the UI is in its default state. Use `data-testid` to click 'Clear' or 'Reset' buttons at the start of a `beforeEach` or at the beginning of a test.
```typescript
// Example: Resetting the report pack
const clearBtn = page.getByTestId("clear-pack-button");
if (await clearBtn.isVisible()) {
    await clearBtn.click();
}
```

### 2. Pre-emptive `waitForResponse`
To eliminate sync race conditions, capture the response promise BEFORE the click.
```typescript
// ✅ CORRECT:
const responsePromise = page.waitForResponse(r => r.url().includes("/api/sync") && r.status() === 200);
await page.getByRole("button", { name: "Save" }).click();
const response = await responsePromise;

// ❌ INCORRECT:
await page.getByRole("button", { name: "Save" }).click();
const response = await page.waitForResponse(...); // Response may have already arrived!
```

### 3. Hydration Sentinels
Ensure the React/Expo SPA is fully interactive before clicking. Use a combination of path verification, element visibility, and font readiness.
```typescript
export async function waitForJudgeApp(page: Page) {
    // 1. Path check (supports monolith rewrites)
    await page.waitForFunction(() => window.location.pathname.includes("/judge"));
    // 2. Element check (wait for a core interactive element)
    await expect(page.getByPlaceholder("Your Name")).toBeVisible({ timeout: 30000 });
    // 3. Font check (prevents layout shifts during click)
    await page.evaluate(() => document.fonts.ready);
}
```

### 4. Robust Click Fallback
If standard `click()` fails due to pointer-event interception in mobile emulation, use a script-based fallback.
```typescript
export async function robustClick(locator: Locator) {
    try {
        await locator.click({ timeout: 5000 });
    } catch (e) {
        await locator.evaluate((el) => (el as HTMLElement).click());
    }
}
```

## 🔍 Validation Checklist
- [ ] Does the test clear global state (LocalStorage, Report Pack)?
- [ ] Are all `waitForResponse` calls initialized before the trigger?
- [ ] Does the Judge App test use `waitForJudgeApp`?
- [ ] Is the `idToken` cookie injected for middleware bypass?
