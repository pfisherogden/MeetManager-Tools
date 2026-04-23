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

test.describe("Champs Dataset Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		const userId = `e2e-champs-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;

		page.on("console", (msg) =>
			console.log(`BROWSER [${userId}]:`, msg.text()),
		);

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
	}, testInfo) => {
		// Set reasonable timeout
		test.setTimeout(180000);

		// Use helper for robust dataset management in CI
		const userId = `e2e-champs-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
		const testFileName = "tiny_champs.json";
		const tinyChampsData = JSON.parse(
			fs.readFileSync(
				path.resolve(process.cwd(), "..", "tests", "fixtures", testFileName),
				"utf8",
			),
		);

		await ensureDataset(page, userId, testFileName, tinyChampsData);

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
		await clubCard.evaluate((el) => (el as HTMLElement).click());

		// Add 2 reports to the pack (sufficient for testing bundle logic)
		for (let i = 0; i < 2; i++) {
			await page
				.getByRole("button", { name: /Add to Pack/i })
				.evaluate((el) => (el as HTMLElement).click());
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
		const downloadPromise = page.waitForEvent("download", { timeout: 180000 });
		await generateZipBtn.click({ force: true });

		// Wait for the job to complete (success toast)
		await expect(
			page.getByText(/Custom pack generated successfully/i),
		).toBeVisible({ timeout: 120000 });

		const download = await downloadPromise;
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
