import * as fs from "node:fs";
import * as path from "node:path";
import { expect, type Page, test } from "@playwright/test";

async function ensureDataset(
	page: Page,
	uid: string,
	filename: string,
	data: any,
) {
	console.log(`Ensuring dataset for ${uid}: ${filename}...`);
	await page.goto(`/admin?uid=${uid}`);

	// Wait for the main container to be ready
	await expect(
		page.getByRole("heading", { name: /Admin Configuration/i }),
	).toBeVisible({ timeout: 20000 });

	// Use the specific row for this user's dataset if multiple exist
	const row = page.getByTestId(`dataset-row-${filename}`);

	// Wait for the row to appear with retries (handle stale lists in CI)
	console.log(`Initial check for row: dataset-row-${filename}...`);
	for (let i = 0; i < 5; i++) {
		if ((await row.count()) > 0) break;
		console.log(`Retry ${i + 1}: Row not found, reloading with cache bust...`);
		// Force cache bust via URL parameter
		await page.goto(`/admin?uid=${uid}&t=${Date.now()}`, {
			waitUntil: "networkidle",
		});
		await page.waitForTimeout(3000);
	}

	const rowCount = await row.count();
	if (rowCount > 0) {
		const isActive =
			(await row.getByTestId("active-dataset-badge").count()) > 0;
		if (isActive) {
			console.log(`Dataset ${filename} is already active for ${uid}`);
			return;
		}
	}

	// Not active or not found, check if uploaded
	if (rowCount === 0) {
		console.log(`No dataset ${filename} found for ${uid}, uploading...`);
		const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
		if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
		const testFilePath = path.join(tempDir, filename);
		fs.writeFileSync(testFilePath, JSON.stringify(data));

		try {
			const fileChooserPromise = page.waitForEvent("filechooser");
			// Use evaluate click for maximum reliability in CI
			await page.evaluate(() => {
				const buttons = Array.from(document.querySelectorAll("button"));
				const uploadBtn = buttons.find((b) =>
					b.innerText.includes("Upload Dataset"),
				);
				if (uploadBtn) uploadBtn.click();
			});
			const fileChooser = await fileChooserPromise;
			await fileChooser.setFiles(testFilePath);
			await expect(
				page.getByText(/Dataset uploaded successfully/i),
			).toBeVisible({ timeout: 20000 });

			// Wait for the specific row to appear after upload with retries
			console.log(`Waiting for row to appear: dataset-row-${filename}...`);
			let rowVisible = false;
			for (let i = 0; i < 5; i++) {
				const count = await row.count();
				if (count > 0 && (await row.isVisible())) {
					rowVisible = true;
					break;
				}
				console.log(`Retry ${i + 1}: Row not found after upload, reloading...`);
				// Force cache bust via URL parameter
				await page.goto(`/admin?uid=${uid}&t=${Date.now()}`, {
					waitUntil: "networkidle",
				});
				await page.waitForTimeout(3000);
			}

			if (!rowVisible) {
				console.log("FINAL ATTEMPT: Waiting for row visibility...");
			}
			await expect(row).toBeVisible({ timeout: 15000 });
		} finally {
			if (fs.existsSync(testFilePath)) fs.unlinkSync(testFilePath);
		}
	}

	// Now set it active
	console.log(`Setting ${filename} active...`);
	await page.evaluate((fid) => {
		const row = document.querySelector(`[data-testid="dataset-row-${fid}"]`);
		const buttons = Array.from(row?.querySelectorAll("button") || []);
		const btn = buttons.find((b) => b.innerText.includes("Set Active"));
		if (btn) (btn as HTMLElement).click();
	}, filename);

	await expect(row.getByTestId("active-dataset-badge")).toBeVisible({
		timeout: 15000,
	});
	console.log(`Dataset ${filename} is now active`);
}

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
		// Use helper for robust dataset management in CI
		const userId = `e2e-reports-${test.info().workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		const testFileName = "tiny_meet.json";
		const tinyMeetData = JSON.parse(
			fs.readFileSync(
				path.resolve(process.cwd(), "..", "tests", "fixtures", testFileName),
				"utf8",
			),
		);

		await ensureDataset(page, userId, testFileName, tinyMeetData);

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
