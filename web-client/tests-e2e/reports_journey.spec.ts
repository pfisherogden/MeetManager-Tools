import { expect, test } from "@playwright/test";

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/reports");
		await expect(
			page.getByRole("heading", { name: "Reports", exact: true }),
		).toBeVisible();
	});

	test("should generate and preview HTML Meet Program", async ({ page }) => {
		// 1. Select the "Meet Program (HTML)" card
		const htmlCard = page.getByTestId("report-card-meet-program-(html)");
		await htmlCard.click();

		// 2. Verify configuration summary updates
		await expect(page.locator("div").filter({ hasText: /^Summary/ })).toContainText("Meet Program (HTML)");

		// 3. Click "View HTML" button
		await page.getByRole("button", { name: "View HTML" }).click();

		// 4. Verify preview dialog opens
		const dialog = page.getByRole("dialog");
		await expect(dialog).toBeVisible({ timeout: 30000 });
		await expect(dialog.getByText("Meet Program Preview")).toBeVisible();

		// 5. Verify iframe content (Wait for iframe to load and have content)
		const iframe = page.frameLocator('iframe[title="Meet Program Preview"]');
		
		// The HTML report should contain "Event" and "Heat" markers
		// Using regex to be flexible with exact text like "Event 1"
		await expect(iframe.getByText(/Event/i).first()).toBeVisible({ timeout: 10000 });
		await expect(iframe.getByText(/Heat/i).first()).toBeVisible();
		
		// Verify some data exists - shouldn't just be a header
		// In the sample data, we expect multiple events
		const eventText = await iframe.locator('body').innerText();
		const eventMatches = eventText.match(/Event \d+/g);
		expect(eventMatches && eventMatches.length).toBeGreaterThan(0);
	});

	test("should generate PDF Entries report", async ({ page }) => {
		// 1. Select the "Entries (Club Style)" card
		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.click();

		// 2. Click "Download PDF" button
		// Note: We don't actually download the file in E2E to avoid side effects,
		// but we check if the toast appears indicating success.
		await page.getByRole("button", { name: "Download PDF" }).click();

		// 3. Verify success toast
		await expect(page.getByText("Report generated successfully")).toBeVisible({ timeout: 30000 });
	});

	test("should verify other report types are selectable", async ({ page }) => {
		const types = [
			"Psych Sheet",
			"Meet Entries",
			"Lineup Sheets",
			"Meet Results",
			"Entries (HY-TEK Style)"
		];

		for (const type of types) {
			const testId = `report-card-${type.toLowerCase().replace(/\s+/g, "-")}`;
			await page.getByTestId(testId).click();
			await expect(page.locator("div").filter({ hasText: /^Summary/ })).toContainText(type);
		}
	});
});
