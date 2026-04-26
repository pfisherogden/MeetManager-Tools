import { expect, test } from "@playwright/test";
import { getE2ETestContext, robustClick } from "./utils";

test.describe("Mobile Judge App Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
		await page.setExtraHTTPHeaders({ "x-user-id": userId });
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
		console.log(`Using isolated Judge User ID: ${userId}`);
	});

	// Set baseURL to the judge app endpoint.
	// In local dev, the judge app is mounted as a static directory in the frontend.
	test.use({
		baseURL: process.env.MOBILE_APP_URL || "http://localhost:3000/judge/",
		viewport: { width: 390, height: 1200 }, // Ensure tall enough for all DQ codes
	});

	test("should allow a judge to login, select event, and submit DQ", async ({
		page,
	}, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const { userId } = getE2ETestContext(testInfo);

		// 1. Initial Page: Enter Name
		await page.goto("./");

		// Wait for app to be ready (hydration sentinel)
		await expect(page.getByPlaceholder("Your Name")).toBeVisible({
			timeout: 45000,
		});

		await page.getByPlaceholder("Your Name").fill("E2E Judge");
		await page.getByRole("button", { name: /START JUDGING/i }).click();

		// 2. Meet List: Select Meet
		// Wait for meet data to be fetched from backend (auth check)
		await expect(page.getByText(/Event 1/i)).toBeVisible({ timeout: 60000 });
		await page.getByText(/Event 1/i).click();

		// 3. Heat List: Select Heat
		await expect(page.getByText(/Heat 1/i)).toBeVisible({ timeout: 15000 });
		await page.getByText(/Heat 1/i).click();

		// 4. Heat Detail: Click a swimmer to DQ
		// Look for "TAP TO DQ" button
		const dqBtn = page.getByRole("button", { name: /TAP TO DQ/i }).first();
		await expect(dqBtn).toBeVisible({ timeout: 15000 });
		await dqBtn.click();

		// 5. Verify DQ Modal opens
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).toBeVisible();

		// 6. Select a DQ code (e.g., "1A") via new data-testid
		const code1A_selector = "[data-testid='dq-code-1A']";
		await page.waitForSelector(code1A_selector, {
			state: "attached",
			timeout: 10000,
		});

		// Use evaluate click for Safari robustness
		await page.evaluate((sel) => {
			const el = document.querySelector(sel);
			if (el) (el as HTMLElement).click();
		}, code1A_selector);

		// 7. Add Note and Submit
		await page
			.getByPlaceholder("Add notes here (optional)")
			.fill("E2E Test Note");
		await page.getByRole("button", { name: /SUBMIT DQ/i }).click();

		// 8. Verify submission (wait for modal to close or history to update)
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).not.toBeVisible();

		// 9. Sync Data (Offline -> Online)
		const syncBtn = page.getByTestId("dq-history-button");
		await expect(syncBtn).toBeVisible({ timeout: 15000 });
		await robustClick(syncBtn, { timeout: 30000 });

		await expect(page.getByText(/Successfully synced/i)).toBeVisible({
			timeout: 45000,
		});
		await expect(page.getByText(/DQ History \(Pending: 0\)/)).toBeVisible();
	});
});
