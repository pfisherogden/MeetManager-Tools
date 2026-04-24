import { expect, test } from "@playwright/test";

test.describe("Mobile Judge App Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		const userId = `e2e-judge-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;

		// Set header for all requests from this page
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
		});

		// Set cookie for additional resilience
		await context.addCookies([
			{
				name: "x-user-id",
				value: userId,
				domain: "localhost",
				path: "/",
			},
		]);

		console.log(`Using isolated User ID: ${userId}`);
	});

	// Set baseURL to the mobile app port (8080 by default in Docker)
	test.use({ baseURL: process.env.MOBILE_APP_URL || "http://localhost:8080" });

	test("should allow adding a DQ in individual event", async ({ page }) => {
		await page.goto("/");

		// 0. Handle Judge Name Prompt
		await page.getByPlaceholder("Your Name").fill("E2E Test Judge");
		await page.getByText("START JUDGING").click();

		// 1. Verify we are on the Events view
		await expect(page.getByText("Events", { exact: true })).toBeVisible();

		// 2. Tap an individual event (e.g., Event 1)
		await page
			.getByText(/#1 |Event 1/i)
			.first()
			.evaluate((el) => (el as HTMLElement).click());

		// 3. Tap a heat (e.g., Heat 1)
		await page
			.getByText(/Heat 1/i)
			.first()
			.evaluate((el) => (el as HTMLElement).click());

		// 4. Tap "TAP TO DQ" for a swimmer
		const tapToDq = page.getByText("TAP TO DQ").first();
		await expect(tapToDq).toBeVisible();
		await tapToDq.evaluate((el) => (el as HTMLElement).click());

		// 5. Verify DQ Modal opens
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).toBeVisible();

		// 6. Select a DQ code (e.g., "1A")
		await page
			.getByText("1A")
			.first()
			.evaluate((el) => (el as HTMLElement).click());

		// 7. Add a note
		await page
			.getByPlaceholder("Add notes here (optional)")
			.fill("Test DQ Note");

		// 8. Tap Save (checkmark-circle icon)
		await page
			.getByLabel("Save changes")
			.evaluate((el) => (el as HTMLElement).click());

		// 9. Verification: Modal closes and DQ code is displayed
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).not.toBeVisible();
		await expect(page.getByText("1A")).toBeVisible();

		// 10. Verification: DQ History count increments
		await expect(page.getByText(/DQ History \(Pending: 1\)/)).toBeVisible();
	});

	test("should toggle between Event and Program views", async ({ page }) => {
		await page.goto("/");

		// 0. Handle Judge Name Prompt
		await page.getByPlaceholder("Your Name").fill("E2E Test Judge");
		await page.getByText("START JUDGING").click();

		// Default is Event view
		await expect(page.getByText("Events", { exact: true })).toBeVisible();

		// Switch to Program view
		await page
			.getByText("SWITCH TO PROGRAM VIEW")
			.evaluate((el) => (el as HTMLElement).click());

		// Verify Program View is shown
		await expect(page.getByText("SWITCH TO EVENT VIEW")).toBeVisible();

		// In program mode, check if we see event headers
		await expect(page.getByText(/#1 |Event 1/i).first()).toBeVisible();

		// Switch back
		await page
			.getByText("SWITCH TO EVENT VIEW")
			.evaluate((el) => (el as HTMLElement).click());
		await expect(page.getByText("Events", { exact: true })).toBeVisible();
	});

	test("should support offline-first DQ entry with network recovery", async ({
		page,
		context,
	}) => {
		await page.goto("/");
		await page.getByPlaceholder("Your Name").fill("Offline Judge");
		await page.getByText("START JUDGING").click();

		// 1. Go Offline
		console.log("[Test] Going OFFLINE...");
		await context.setOffline(true);

		// 2. Add DQ while offline
		await page
			.getByText(/#1 |Event 1/i)
			.first()
			.evaluate((el) => (el as HTMLElement).click());
		await page
			.getByText(/Heat 1/i)
			.first()
			.evaluate((el) => (el as HTMLElement).click());
		await page
			.getByText("TAP TO DQ")
			.first()
			.evaluate((el) => (el as HTMLElement).click());
		await page
			.getByText("1A")
			.first()
			.evaluate((el) => (el as HTMLElement).click());
		await page
			.getByLabel("Save changes")
			.evaluate((el) => (el as HTMLElement).click());

		// 3. Verify it is pending locally
		await expect(page.getByText(/DQ History \(Pending: 1\)/)).toBeVisible();

		// 4. Go Online
		console.log("[Test] Going ONLINE...");
		await context.setOffline(false);
		await page.waitForTimeout(2000); // Wait for network stack to recover

		// 5. Trigger Sync and verify
		console.log("[Test] Opening DQ History...");
		const historyTrigger = page.getByText(/DQ History \(Pending: 1\)/);
		await historyTrigger.evaluate((el) => (el as HTMLElement).click());

		console.log("[Test] Waiting for SYNC NOW button...");
		const syncBtn = page.getByText("SYNC NOW");
		await expect(syncBtn).toBeVisible({ timeout: 30000 });

		console.log("[Test] Clicking SYNC NOW...");
		await syncBtn.evaluate((el) => (el as HTMLElement).click());

		await expect(page.getByText(/Successfully synced/i)).toBeVisible({
			timeout: 45000,
		});
		await expect(page.getByText(/DQ History \(Pending: 0\)/)).toBeVisible();
	});
});
