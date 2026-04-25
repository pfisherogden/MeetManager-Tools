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

	// Set baseURL to the mobile app port (8082 by default in local Docker, 8081 in CI)
	test.use({
		baseURL: process.env.MOBILE_APP_URL || "http://localhost:8082",
		viewport: { width: 390, height: 1200 }, // Ensure tall enough for all DQ codes
	});

	test("should allow adding a DQ in individual event", async ({ page }) => {
		await page.goto("/");

		// 0. Handle Judge Name Prompt
		await page.getByPlaceholder("Your Name").fill("E2E Test Judge");
		await page.getByText("START JUDGING").click({ force: true });

		// 1. Verify we are on the Events view
		await expect(page.getByText("Events", { exact: true })).toBeVisible();

		// 2. Tap an individual event (e.g., Event 1)
		const event1 = page.getByText(/#1 |Event 1/i).first();
		await event1.scrollIntoViewIfNeeded();
		await event1.click({ force: true });

		// 3. Tap a heat (e.g., Heat 1)
		const heat1 = page.getByText(/Heat 1/i).first();
		await heat1.scrollIntoViewIfNeeded();
		await heat1.click({ force: true });

		// 4. Tap "TAP TO DQ" for a swimmer
		const tapToDq = page.getByText("TAP TO DQ").first();
		await expect(tapToDq).toBeVisible();
		await tapToDq.scrollIntoViewIfNeeded();
		await tapToDq.click({ force: true });

		// 5. Verify DQ Modal opens
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).toBeVisible();

		// 6. Select a DQ code (e.g., "1A")
		const code1A = page.getByText("1A").first();
		await code1A.scrollIntoViewIfNeeded();
		await code1A.click({ force: true });

		// 7. Add a note
		await page
			.getByPlaceholder("Add notes here (optional)")
			.fill("Test DQ Note");

		// 8. Tap Save (checkmark-circle icon)
		const saveBtn = page.getByLabel("Save changes");
		await saveBtn.scrollIntoViewIfNeeded();
		await saveBtn.click({ force: true });

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
		await page.getByText("START JUDGING").click({ force: true });

		// Default is Event view
		await expect(page.getByText("Events", { exact: true })).toBeVisible();

		// Switch to Program view
		const programBtn = page.getByText("SWITCH TO PROGRAM VIEW");
		await programBtn.scrollIntoViewIfNeeded();
		await programBtn.click({ force: true });

		// Verify Program View is shown
		await expect(page.getByText("SWITCH TO EVENT VIEW")).toBeVisible();

		// In program mode, check if we see event headers
		await expect(page.getByText(/#1 |Event 1/i).first()).toBeVisible();

		// Switch back
		const eventViewBtn = page.getByText("SWITCH TO EVENT VIEW");
		await eventViewBtn.scrollIntoViewIfNeeded();
		await eventViewBtn.click({ force: true });
		await expect(page.getByText("Events", { exact: true })).toBeVisible();
	});

	test("should manage offline queue (clear all)", async ({ page }) => {
		await page.goto("/");

		// 0. Handle Judge Name Prompt
		await page.getByPlaceholder("Your Name").fill("E2E Test Judge");
		await page.getByText("START JUDGING").click({ force: true });

		// Add a DQ first
		await page
			.getByText(/#1 |Event 1/i)
			.first()
			.click({ force: true });
		await page
			.getByText(/Heat 1/i)
			.first()
			.click({ force: true });
		await page.getByText("TAP TO DQ").first().click({ force: true });
		await page.getByText("1A").first().click({ force: true });
		await page.getByLabel("Save changes").click({ force: true });

		await expect(page.getByText(/DQ History \(Pending: 1\)/)).toBeVisible();

		// Open DQ History
		const historyBtn = page.getByText(/DQ History \(Pending: 1\)/);
		await historyBtn.scrollIntoViewIfNeeded();
		await historyBtn.click({ force: true });
		await page.waitForTimeout(1500); // Allow modal transition

		// Verify modal content
		await expect(page.getByText("DQ History (Total: 1)")).toBeVisible();
		await expect(page.getByText(/CLEAR PENDING/i)).toBeVisible();

		// Clear Pending
		await page.getByText(/CLEAR PENDING/i).click({ force: true });

		// Verification
		await expect(page.getByText("No DQs recorded")).toBeVisible();

		// Close modal
		await page.keyboard.press("Escape");
		await page.waitForTimeout(1000);

		const closeBtn = page.getByLabel("Close history");
		if (await closeBtn.isVisible()) {
			await closeBtn.click({ force: true });
		}

		// Queue count should be 0
		await expect(page.getByText(/DQ History \(Pending: 0\)/)).toBeVisible();
	});

	test("should support offline-first DQ entry with network recovery", async ({
		page,
		context,
	}) => {
		await page.goto("/");
		await page.getByPlaceholder("Your Name").fill("Offline Judge");
		await page.getByText("START JUDGING").click({ force: true });

		// 1. Go Offline
		console.log("[Test] Going OFFLINE...");
		await context.setOffline(true);

		// 2. Add DQ while offline
		await page
			.getByText(/#1 |Event 1/i)
			.first()
			.click({ force: true });
		await page
			.getByText(/Heat 1/i)
			.first()
			.click({ force: true });
		await page.getByText("TAP TO DQ").first().click({ force: true });
		await page.getByText("1A").first().click({ force: true });
		await page.getByLabel("Save changes").click({ force: true });

		// 3. Verify it is pending locally
		await expect(page.getByText(/DQ History \(Pending: 1\)/)).toBeVisible();

		// 4. Go Online
		console.log("[Test] Going ONLINE...");
		await context.setOffline(false);
		await page.waitForTimeout(3000); // Wait longer for network stack to recover

		// 5. Trigger Sync and verify
		console.log("[Test] Opening DQ History...");
		const historyTrigger = page.getByText(/DQ History \(Pending: 1\)/);
		await historyTrigger.scrollIntoViewIfNeeded();
		await historyTrigger.click({ force: true });
		await page.waitForTimeout(2000); // Allow modal rendering

		console.log("[Test] Waiting for SYNC NOW button...");
		const syncBtn = page.getByRole("button", { name: /SYNC NOW/i });
		await expect(syncBtn).toBeVisible({ timeout: 30000 });

		console.log("[Test] Clicking SYNC NOW...");
		await syncBtn.scrollIntoViewIfNeeded();
		await syncBtn.click({ force: true });

		await expect(page.getByText(/Successfully synced/i)).toBeVisible({
			timeout: 45000,
		});
		await expect(page.getByText(/DQ History \(Pending: 0\)/)).toBeVisible();
	});
});
