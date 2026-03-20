import { expect, test } from "@playwright/test";

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		const userId = `e2e-reports-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;

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

	test("should ensure Sample_Data.json is active and navigate to Reports", async ({
		page,
	}) => {
		// 1. Go to Admin to ensure Sample_Data.json is active
		await page.goto("/admin", { waitUntil: "networkidle" });

		const sampleRow = page.locator("tr").filter({
			has: page.locator("td", {
				hasText: /^Sample_Data.json$/i,
			}),
		});

		if ((await sampleRow.count()) > 0) {
			const activeBadge = sampleRow.locator("text=/Active/i");
			if (await activeBadge.isHidden()) {
				console.log("Setting Sample_Data.json as active for report tests...");
				await sampleRow.getByRole("button", { name: "Set Active" }).click();
				await expect(activeBadge).toBeVisible({ timeout: 20000 });
			}
		}

		// 2. Go to Reports
		await page.goto("/reports", { waitUntil: "networkidle" });
		await expect(
			page.getByRole("heading", { name: "Reports", exact: true }),
		).toBeVisible({ timeout: 30000 });
	});

	test("should generate and preview HTML Meet Program", async ({ page }) => {
		// Ensure we are on reports page
		await page.goto("/reports", { waitUntil: "networkidle" });

		// 1. Select the "Meet Program (HTML)" card
		const htmlCard = page.getByTestId("report-card-meet-program-(html)");
		await htmlCard.click();

		// 2. Verify configuration summary updates
		await expect(
			page.locator("div").filter({ hasText: /^Summary/ }),
		).toContainText("Meet Program (HTML)");

		// 3. Click "View HTML" button
		await page.getByRole("button", { name: "View HTML" }).click();

		// 4. Verify preview dialog opens
		const dialog = page.getByRole("dialog");
		await expect(dialog).toBeVisible({ timeout: 60000 });
		await expect(dialog.getByText("Meet Program Preview")).toBeVisible();

		// 5. Verify iframe content (Wait for iframe to load and have content)
		// Delay to allow srcDoc to render
		await page.waitForTimeout(10000);
		const iframe = page.frameLocator('iframe[title="Meet Program Preview"]');

		// The HTML report should contain "Event" and "Heat" markers
		// Use a more robust check by looking at the full text content
		const bodyText = await iframe.locator("body").innerText();
		console.log("HTML Report Preview Content:", bodyText);
		console.log("HTML Report Preview Length:", bodyText.length);

		// Verified fix: Report should have substantial content
		expect(bodyText.length).toBeGreaterThan(500);
		expect(bodyText.toLowerCase()).toContain("event");
		expect(bodyText.toLowerCase()).toContain("heat");
	});

	test("should generate PDF Entries report", async ({ page }) => {
		// Ensure we are on reports page
		await page.goto("/reports", { waitUntil: "networkidle" });

		// 1. Select the "Entries (Club Style)" card
		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.click();

		// 2. Click "Download PDF" button
		// Note: We don't actually download the file in E2E to avoid side effects,
		// but we check if the toast appears indicating success.
		await page.getByRole("button", { name: "Download PDF" }).click();

		// 3. Verify success toast
		await expect(page.getByText("Report generated successfully")).toBeVisible({
			timeout: 30000,
		});
	});

	test("should verify other report types are selectable", async ({ page }) => {
		// Ensure we are on reports page
		await page.goto("/reports", { waitUntil: "networkidle" });

		const types = [
			"Psych Sheet",
			"Meet Entries",
			"Lineup Sheets",
			"Meet Results",
			"Entries (HY-TEK Style)",
		];

		for (const type of types) {
			const testId = `report-card-${type.toLowerCase().replace(/\s+/g, "-")}`;
			await page.getByTestId(testId).click();
			await expect(
				page.locator("div").filter({ hasText: /^Summary/ }),
			).toContainText(type);
		}
	});
});
