import * as path from "node:path";
import { expect, test } from "@playwright/test";

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page }) => {
		// 1. Go to Meets and upload the champs MDB
		await page.goto("/");
		try {
			await page
				.locator("nav")
				.getByRole("link", { name: "Meets", exact: true })
				.click({ timeout: 10000 });
		} catch (_e) {
			console.log(
				"Sidebar click failed, falling back to direct navigation to /meets",
			);
			await page.goto("/meets");
		}

		await expect(
			page.getByRole("heading", { name: "Dataset Management" }),
		).toBeVisible({ timeout: 30000 });

		// Check if champs dataset is already active
		const champsRow = page.locator("tr", {
			hasText: "sample_data_champs_2025-aftermeet.mdb",
		});
		const isActive = await champsRow.locator("text=Active").isVisible();

		if (!isActive) {
			const fileChooserPromise = page.waitForEvent("filechooser");
			await page.getByRole("button", { name: "Upload Dataset" }).click();
			const fileChooser = await fileChooserPromise;

			// Path relative to the web-client directory where playwright runs
			const mdbPath = path.join(
				__dirname,
				"../../../backend/data/sample_data_champs_2025-aftermeet.mdb",
			);
			await fileChooser.setFiles(mdbPath);

			// Wait for upload success toast or the active badge
			await Promise.race([
				expect(page.getByText("Dataset uploaded successfully")).toBeVisible({
					timeout: 60000,
				}),
				expect(champsRow.locator("text=Active")).toBeVisible({
					timeout: 60000,
				}),
			]);
		}

		// 2. Go to Reports
		try {
			await page
				.locator("nav")
				.getByRole("link", { name: "Reports", exact: true })
				.click({ timeout: 10000 });
		} catch (_e) {
			console.log(
				"Sidebar click failed, falling back to direct navigation to /reports",
			);
			await page.goto("/reports");
		}

		await expect(
			page.getByRole("heading", { name: "Reports", exact: true }),
		).toBeVisible();
	});

	test("should generate and preview HTML Meet Program", async ({ page }) => {
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
		await page.waitForTimeout(20000);
		const iframe = page.frameLocator('iframe[title="Meet Program Preview"]');

		// The HTML report should contain "Event" and "Heat" markers
		// Use a more robust check by looking at the full text content
		const bodyText = await iframe.locator("body").innerText();
		console.log("HTML Report Preview Length:", bodyText.length);

		// Verified fix with Champs data: Report should have substantial content
		expect(bodyText.length).toBeGreaterThan(500);
		expect(bodyText.toLowerCase()).toContain("event");
		expect(bodyText.toLowerCase()).toContain("heat");
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
		await expect(page.getByText("Report generated successfully")).toBeVisible({
			timeout: 30000,
		});
	});

	test("should verify other report types are selectable", async ({ page }) => {
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
