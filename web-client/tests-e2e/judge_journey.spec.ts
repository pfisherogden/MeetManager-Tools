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

		// 1. Verify we are on the Events view
		await expect(page.getByText("Events", { exact: true })).toBeVisible();

		// 2. Tap an individual event (e.g., Event 1)
		// Assuming seed data has Event 1.
		// Use a more robust selector that works for both "Event 1" and "#1"
		await page
			.getByText(/#1 |Event 1/i)
			.first()
			.click();

		// 3. Tap a heat (e.g., Heat 1)
		await page
			.getByText(/Heat 1/i)
			.first()
			.click();

		// 4. Tap "TAP TO DQ" for a swimmer
		await expect(page.getByText("TAP TO DQ").first()).toBeVisible();
		await page.getByText("TAP TO DQ").first().click();

		// 5. Verify DQ Modal opens
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).toBeVisible();

		// 6. Select a DQ code (e.g., "1A")
		// The code is usually in a text element next to description
		await page.getByText("1A").first().click();

		// 7. Add a note
		await page
			.getByPlaceholder("Add notes here (optional)")
			.fill("Test DQ Note");

		// 8. Tap Save (checkmark-circle icon)
		await page.getByLabel("Save changes").click();

		// 9. Verification: Modal closes and DQ code is displayed
		await expect(
			page.getByPlaceholder("Add notes here (optional)"),
		).not.toBeVisible();
		await expect(page.getByText("1A")).toBeVisible();

		// 10. Verification: Offline Queue count increments
		await expect(page.getByText(/Offline Queue: 1/)).toBeVisible();
	});

	test("should toggle between Event and Program views", async ({ page }) => {
		await page.goto("/");

		// Default is Event view
		await expect(page.getByText("Events", { exact: true })).toBeVisible();

		// Switch to Program view
		await page.getByText("SWITCH TO PROGRAM VIEW").click();

		// Verify Program View is shown (Continuous list)
		// The ProgramView component has different structure
		await expect(page.getByText("SWITCH TO EVENT VIEW")).toBeVisible();

		// In program mode, check if we see event headers
		await expect(page.getByText(/#1 |Event 1/i).first()).toBeVisible();

		// Switch back
		await page.getByText("SWITCH TO EVENT VIEW").click();
		await expect(page.getByText("Events", { exact: true })).toBeVisible();
	});

	test("should manage offline queue (clear all)", async ({ page }) => {
		await page.goto("/");

		// Add a DQ first
		await page
			.getByText(/#1 |Event 1/i)
			.first()
			.click();
		await page
			.getByText(/Heat 1/i)
			.first()
			.click();
		await page.getByText("TAP TO DQ").first().click();
		await page.getByText("1A").first().click();
		await page.getByLabel("Save changes").click();

		await expect(page.getByText(/Offline Queue: 1/)).toBeVisible();

		// Open Offline Queue
		await page.getByText(/Offline Queue: 1/).click();

		// Verify modal content
		await expect(page.getByText("Offline Queue (1)")).toBeVisible();
		await expect(page.getByText("CLEAR ALL")).toBeVisible();

		// Clear All
		await page.getByText("CLEAR ALL").click();

		// Verification
		await expect(page.getByText("No pending DQs")).toBeVisible();

		// Close modal
		await page.keyboard.press("Escape");
		await page.waitForTimeout(1000);
		// If still visible, try accessibility label or click outside
		if (await page.getByText("Offline Queue").first().isVisible()) {
			const closeButton = page.getByLabel("Close offline queue");
			if (await closeButton.isVisible()) {
				await closeButton.click();
			} else {
				await page.mouse.click(10, 10);
			}
		}

		// Queue count should be 0
		await expect(page.getByText(/Offline Queue: 0/)).toBeVisible();
	});
});
