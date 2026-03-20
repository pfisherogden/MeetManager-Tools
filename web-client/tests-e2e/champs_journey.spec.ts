import * as path from "node:path";
import { expect, test } from "@playwright/test";

test.describe("Champs Dataset Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		// Set a unique user ID for this test to avoid collisions in the backend
		const userId = `e2e-champs-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;

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

	test("should correctly process and display Champs 2025 dataset", async ({
		page,
	}, _testInfo) => {
		// Set higher timeout for this complex journey
		test.setTimeout(240000);

		// 1. Admin: Upload and Set Active
		await page.goto("/admin", { waitUntil: "networkidle" });
		const testFileName = "anonymized_champs.json";
		const testFilePath = process.env.CI
			? path.join(process.cwd(), "..", "tests", "fixtures", testFileName)
			: path.resolve(__dirname, `../../../tests/fixtures/${testFileName}`);

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
		const uploadBtn = page.getByText("Upload Dataset");
		await expect(uploadBtn).toBeVisible({ timeout: 20000 });
		await uploadBtn.click();
		const fileChooser = await fileChooserPromise;
		await fileChooser.setFiles(testFilePath);
		await expect(page.getByText(/Dataset uploaded successfully/i)).toBeVisible({
			timeout: 60000,
		});

		// Set as active
		const datasetRow = page.locator("tr").filter({
			has: page.locator("td", {
				hasText: new RegExp(`^${testFileName}$`),
			}),
		});
		await expect(datasetRow.first()).toBeVisible({ timeout: 20000 });

		const setActiveBtn = datasetRow.getByRole("button", { name: "Set Active" });
		const activeBadge = datasetRow.locator("text=/Active/i");

		if (await activeBadge.isHidden()) {
			console.log("Setting dataset as active...");
			await setActiveBtn.click();
			await expect(activeBadge).toBeVisible({ timeout: 30000 });
			// Give extra time for backend to switch and cache to clear
			await page.waitForTimeout(5000);
		} else {
			console.log("Dataset already active.");
		}

		// 2. Meets Page: Verify name and location
		await page.goto("/meets", { waitUntil: "networkidle" });
		// Wait for table to NOT have "No data available" if possible, or just wait for timeout
		await page.waitForTimeout(3000);
		await expect(page.locator("table")).toContainText(
			"TVSL Championship Meet 2025",
			{ timeout: 20000 },
		);
		await expect(page.locator("table")).toContainText("Foothill High School");

		// 3. Teams Page: Verify data visibility
		await page.goto("/teams");
		// Using anonymized team name
		await expect(page.locator("table")).toContainText("Blue Dolphins", {
			timeout: 20000,
		});

		// 4. Athletes Page: Verify list
		await page.goto("/athletes");
		await expect(page.locator("table")).toContainText("Dolphins", {
			timeout: 20000,
		});

		// 5. Entries Page: Verify data
		await page.goto("/entries");
		await expect(page.locator("table")).toContainText("Dolphins", {
			timeout: 20000,
		});

		// 6. Reports Page: Generate custom pack
		await page.goto("/reports");
		
		// Select a report type first
		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.click();

		// Add to pack to enable the generate button
		await page.getByRole("button", { name: /Add to Pack/i }).click();
		await expect(page.getByText(/Added to custom pack/i)).toBeVisible();

		const generateZipBtn = page.getByRole("button", {
			name: /Generate Bundle ZIP/i,
		});
		await expect(generateZipBtn).toBeEnabled();
		await generateZipBtn.click();

		await expect(
			page.getByText("Custom pack generated successfully", { exact: false }),
		).toBeVisible({ timeout: 180000 });
	});
});
