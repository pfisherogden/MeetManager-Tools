import * as path from "node:path";
import { expect, test } from "@playwright/test";

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		const userId = `e2e-reports-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;

		// Set header for all requests from this page
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
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

	test("should ensure tiny_meet.json is active and navigate to Reports", async ({
		page,
	}) => {
		// 1. Go to Admin to upload and activate tiny_meet.json
		await page.goto("/admin", { waitUntil: "networkidle" });
		const testFileName = "tiny_meet.json";
		const testFilePath = path.resolve(
			process.cwd(),
			"..",
			"tests",
			"fixtures",
			testFileName,
		);

		console.log(`Using test file path: ${testFilePath}`);

		const fileChooserPromise = page.waitForEvent("filechooser");
		await page.evaluate(() => {
			const buttons = Array.from(document.querySelectorAll("button"));
			const uploadBtn = buttons.find((b) =>
				b.innerText.includes("Upload Dataset"),
			);
			if (uploadBtn) uploadBtn.click();
		});
		const fileChooser = await fileChooserPromise;
		await fileChooser.setFiles(testFilePath);
		await expect(page.getByText(/Dataset uploaded successfully/i)).toBeVisible({
			timeout: 20000,
		});

		const row = page.getByTestId(`dataset-row-${testFileName}`);

		// Wait for the row to appear with retries (handle stale lists in CI)
		console.log(`Waiting for row to appear: dataset-row-${testFileName}...`);
		for (let i = 0; i < 5; i++) {
			if ((await row.count()) > 0) break;
			console.log(`Retry ${i + 1}: Row not found, reloading...`);
			await page.reload({ waitUntil: "networkidle" });
			await page.waitForTimeout(2000);
		}

		await expect(row).toBeVisible({ timeout: 15000 });
		await page.evaluate((fid) => {
			const row = document.querySelector(`[data-testid="dataset-row-${fid}"]`);
			const buttons = Array.from(row?.querySelectorAll("button") || []);
			const btn = buttons.find((b) => b.innerText.includes("Set Active"));
			if (btn) (btn as HTMLElement).click();
		}, testFileName);
		await expect(row.getByTestId("active-dataset-badge")).toBeVisible({
			timeout: 15000,
		});

		// 2. Go to Reports
		await page.goto("/reports", { waitUntil: "networkidle" });
		await expect(
			page.getByRole("heading", { name: "Reports", exact: true }),
		).toBeVisible({ timeout: 30000 });
	});

	test("should generate and preview HTML Meet Program", async ({ page }) => {
		// Ensure we have data (from previous test or session)
		await page.goto("/reports", { waitUntil: "networkidle" });

		const htmlCard = page.getByTestId("report-card-meet-program-(html)");
		await expect(htmlCard).toBeVisible({ timeout: 10000 });
		await htmlCard.click();

		await expect(
			page.locator("div").filter({ hasText: /^Summary/ }),
		).toContainText("Meet Program (HTML)");

		const pagePromise = page.context().waitForEvent("page");
		await page.getByRole("button", { name: "View HTML" }).click();
		const newPage = await pagePromise;
		await newPage.waitForLoadState();

		const bodyText = await newPage.locator("body").innerText();
		expect(bodyText.length).toBeGreaterThan(100); // Tiny meet has less content but still should have some
	});

	test("should generate PDF Entries report", async ({ page }) => {
		await page.goto("/reports", { waitUntil: "networkidle" });

		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.click();

		await page.getByRole("button", { name: "Download PDF" }).click();

		await expect(page.getByText("Report generated successfully")).toBeVisible({
			timeout: 30000,
		});
	});

	test("should verify other report types are selectable", async ({ page }) => {
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
