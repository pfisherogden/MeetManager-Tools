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

		// Set cookie for additional resilience (Next.js can read this if header is missing)
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
	}) => {
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

		const existingRow = page.locator("tr").filter({
			has: page.locator("td", {
				hasText: new RegExp(`^${testFileName}$`),
			}),
		});

		if ((await existingRow.count()) === 0) {
			const fileChooserPromise = page.waitForEvent("filechooser");
			// Use getByText for more resilience
			const uploadBtn = page.getByText("Upload Dataset");
			await expect(uploadBtn).toBeVisible({ timeout: 20000 });
			await uploadBtn.click();
			const fileChooser = await fileChooserPromise;
			await fileChooser.setFiles(testFilePath);
			await expect(
				page.getByText(/Dataset uploaded successfully/i),
			).toBeVisible({ timeout: 60000 });
		}
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

		// 4. Athletes Page: Verify data visibility
		await page.goto("/athletes");
		// Rodriguez is one of the anonymized last names
		await expect(page.locator("table")).toContainText("Rodriguez", {
			timeout: 20000,
		});

		// 5. Entries Page: Verify rounding and Medals
		await page.goto("/entries");
		await expect(page.locator("table tbody tr").first()).toBeVisible({
			timeout: 20000,
		});

		// Verify zebra striping class exists
		const tableRows = page.locator("table tbody tr");
		if ((await tableRows.count()) > 1) {
			const secondRow = tableRows.nth(1);
			const className = await secondRow.getAttribute("class");
			expect(className).toMatch(/bg-muted/);
		}

		// Verify 3-decimal rounding (handle both SS.sss and MM:SS.sss)
		const entryCells = page.locator("table tbody td");
		const cellTexts = await entryCells.allInnerTexts();
		const times = cellTexts.filter((t) =>
			t.match(/(\d+:)?\d+\.\d{3}([ \t\n]|$)/),
		);
		expect(times.length).toBeGreaterThan(0);

		// 6. Scores Page: Bug 4 (Meet Name)
		await page.goto("/scores");
		await expect(page.locator("table tbody tr").first()).toBeVisible({
			timeout: 20000,
		});
		const meetCell = page.locator("table tbody td").nth(2); // 3rd column is Meet
		await expect(meetCell).not.toHaveText("Unknown Meet");

		// 7. Reports: Bug 7, 9, 10, 11
		await page.goto("/reports");
		await page.waitForLoadState("networkidle");

		// Bug 7 & 9: Searchable team filter in Configuration
		const teamTrigger = page.getByTestId("team-filter-trigger");
		await teamTrigger.click();
		await page.getByPlaceholder("Search teams...").fill("Blue Dolphins");
		await page.getByText("Blue Dolphins", { exact: true }).click();
		await expect(teamTrigger).toHaveText("Blue Dolphins");

		// Bug 10: Preset should populate builder
		const presetApplyBtn = page.getByTestId("preset-apply-lineups");
		await presetApplyBtn.click();

		const otherPresetBtn = page.getByTestId("preset-apply-coaches");
		await expect(otherPresetBtn).not.toHaveAttribute("disabled");
		await expect(otherPresetBtn.locator(".animate-spin")).not.toBeVisible();

		const _builderSection = page.locator("#custom-builder");
		await expect(
			page
				.locator("#custom-builder input")
				.filter({ hasValue: /Line Up Report/i })
				.first(),
		).toBeVisible({ timeout: 30000 });

		// Final generation
		const generateZipBtn = page.getByRole("button", {
			name: /Generate Bundle ZIP/i,
		});
		await generateZipBtn.click();

		await expect(
			page.getByText("Custom pack generated successfully", { exact: false }),
		).toBeVisible({ timeout: 180000 });
	});
});
