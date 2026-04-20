import * as fs from "node:fs";
import * as path from "node:path";
import { expect, test } from "@playwright/test";

test.describe("Champs Dataset Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		const userId = `e2e-champs-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;

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

	test("should correctly process and display tiny Champs dataset", async ({
		page,
	}, _testInfo) => {
		// Set reasonable timeout
		test.setTimeout(180000);

		// 1. Admin: Upload and Set Active
		await page.goto("/admin", { waitUntil: "networkidle" });
		const testFileName = "tiny_champs.json";
		const testFilePath = path.resolve(
			process.cwd(),
			"..",
			"tests",
			"fixtures",
			testFileName,
		);

		console.log(`Using test file path: ${testFilePath}`);

		// Wait for any heading or the dataset manager card
		await expect(
			page.getByRole("heading", {
				name: /Admin Configuration|Dataset Management/i,
			}),
		).toBeVisible({ timeout: 30000 });

		// Always upload to ensure clean state for this worker's userId
		console.log(`Uploading dataset: ${testFileName}`);
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
			timeout: 60000,
		});

		// Set as active
		const datasetRow = page.getByTestId(`dataset-row-${testFileName}`);

		// Wait for the row to appear with retries (handle stale lists in CI)
		console.log(`Waiting for row to appear: dataset-row-${testFileName}...`);
		for (let i = 0; i < 5; i++) {
			if ((await datasetRow.count()) > 0) break;
			console.log(
				`Retry ${i + 1}: Row not found, reloading with cache bust...`,
			);
			// Force cache bust via URL parameter
			await page.goto(`/admin?t=${Date.now()}`, {
				waitUntil: "networkidle",
			});
			await page.waitForTimeout(3000);
		}

		await expect(datasetRow).toBeVisible({ timeout: 20000 });

		const activeBadge = datasetRow.getByTestId("active-dataset-badge");

		if (await activeBadge.isHidden()) {
			console.log("Setting dataset as active...");
			await page.evaluate((fid) => {
				const row = document.querySelector(
					`[data-testid="dataset-row-${fid}"]`,
				);
				const buttons = Array.from(row?.querySelectorAll("button") || []);
				const btn = buttons.find((b) => b.innerText.includes("Set Active"));
				if (btn) (btn as HTMLElement).click();
			}, testFileName);
			await expect(activeBadge).toBeVisible({ timeout: 30000 });
			// Give extra time for backend to switch and cache to clear
			await page.waitForTimeout(3000);
		} else {
			console.log("Dataset already active.");
		}

		// 2. Meets Page: Verify name and location
		await page.goto("/meets", { waitUntil: "networkidle" });
		await expect(page.locator("table")).toContainText(
			"TVSL Championship Meet 2025",
			{ timeout: 20000 },
		);

		// 3. Teams Page: Verify data visibility
		await page.goto("/teams");
		// Using anonymized team name
		await expect(page.locator("table")).toContainText("Blue Dolphins", {
			timeout: 20000,
		});

		// 4. Reports Page: Generate custom pack
		await page.goto("/reports");

		// Select a report type first
		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.click();

		// Add 2 reports to the pack (sufficient for testing bundle logic)
		for (let i = 0; i < 2; i++) {
			await page.getByRole("button", { name: /Add to Pack/i }).click();
			await expect(
				page.getByText(/Added to custom pack/i).first(),
			).toBeVisible();
			await page.waitForTimeout(500);
		}

		const generateZipBtn = page.getByRole("button", {
			name: /Generate ZIP/i,
		});
		await expect(generateZipBtn).toBeEnabled();

		console.log("Generating bundle...");

		const [download] = await Promise.all([
			page.waitForEvent("download", { timeout: 120000 }),
			generateZipBtn.click(),
		]);

		console.log("Download initiated...");

		let downloadPath: string | null = null;
		try {
			downloadPath = await download.path();
		} catch (e: any) {
			console.error(`Download failed or was canceled: ${e.message}`);
			throw e;
		}

		expect(downloadPath).toBeTruthy();

		if (downloadPath) {
			const stats = fs.statSync(downloadPath);
			console.log(`Downloaded bundle size: ${stats.size} bytes`);
			// Should have real content
			expect(stats.size).toBeGreaterThan(1024);
		}

		await expect(
			page.getByText("Custom pack generated successfully", { exact: false }),
		).toBeVisible();
	});
});
