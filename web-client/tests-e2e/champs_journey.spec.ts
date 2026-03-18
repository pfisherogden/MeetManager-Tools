import * as path from "node:path";
import { expect, test } from "@playwright/test";

test.describe("Champs Dataset Journey", () => {
	test("should correctly process and display Champs 2025 dataset", async ({
		page,
	}) => {
		test.setTimeout(240000);

		// 1. Admin: Upload and Set Active
		await page.goto("/admin");
		const testFileName = "sample_data_champs_2025-aftermeet.mdb";
		const testFilePath = process.env.CI
			? path.join(process.cwd(), "..", "backend", "data", testFileName)
			: path.resolve(__dirname, `../../backend/data/${testFileName}`);

		console.log(`Using test file path: ${testFilePath}`);

		// Wait for the table to load
		await expect(page.locator("table tbody tr").first()).toBeVisible();

		const existingRow = page.locator("tr").filter({
			has: page.locator("td", {
				hasText: new RegExp(`^${testFileName}$`),
			}),
		});
		if ((await existingRow.count()) === 0) {
			const fileChooserPromise = page.waitForEvent("filechooser");
			await page.getByRole("button", { name: "Upload Dataset" }).click();
			const fileChooser = await fileChooserPromise;
			await fileChooser.setFiles(testFilePath);
			await expect(page.getByText("Dataset uploaded successfully")).toBeVisible(
				{ timeout: 45000 },
			);
		}

		// Set as active
		const datasetRow = page.locator("tr").filter({
			has: page.locator("td", {
				hasText: new RegExp(`^${testFileName}$`),
			}),
		});
		await expect(datasetRow.first()).toBeVisible({ timeout: 10000 });

		const setActiveBtn = datasetRow.getByRole("button", { name: "Set Active" });
		const activeBadge = datasetRow.locator(".bg-green-100, .text-green-700");

		if (await activeBadge.isHidden()) {
			await setActiveBtn.click();
			await expect(activeBadge).toBeVisible({ timeout: 30000 });
			// Give extra time for cache warming
			await page.waitForTimeout(3000);
		}

		// 2. Meets Page: Verify name and location
		await page.goto("/meets");
		await expect(page.locator("table")).toContainText(
			"TVSL Championship Meet 2025",
			{ timeout: 20000 },
		);
		await expect(page.locator("table")).toContainText("Foothill High School");

		// 3. Teams Page: Verify data visibility
		await page.goto("/teams");
		await expect(page.locator("table")).toContainText("Briarhill Swim Team", {
			timeout: 20000,
		});

		// 4. Athletes Page: Verify data visibility
		await page.goto("/athletes");
		await expect(page.locator("table")).toContainText("Bertalotto", {
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

		// Verify medals exist (soft check)
		await expect
			.soft(page.locator(".lucide-trophy").first())
			.toBeVisible({ timeout: 15000 });
		await expect
			.soft(page.locator(".lucide-medal").first())
			.toBeVisible({ timeout: 15000 });

		// Verify 3-decimal rounding
		const entryCells = page.locator("table tbody td");
		const cellTexts = await entryCells.allInnerTexts();
		const times = cellTexts.filter((t) => t.match(/\d+\.\d{3}([ \t\n]|$)/));
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
		// Use specific card-based locators to avoid ambiguity
		const configCard = page.locator("div.rounded-xl", {
			has: page.getByText("Report Configuration"),
		});
		const teamTrigger = configCard.getByRole("combobox");
		await teamTrigger.click();
		await page.getByPlaceholder("Search teams...").fill("Del Prado");
		await page.getByText("Del Prado Stingrays", { exact: true }).click();
		await expect(teamTrigger).toHaveText("Del Prado Stingrays");

		// Bug 10: Preset should populate builder
		await page.getByTestId("preset-apply-lineups").click();

		const builderSection = page.locator("#custom-builder");
		await expect(builderSection.getByText("Line Up Report")).toBeVisible();

		// Bug 11: Zebra striping in builder
		const builderRows = builderSection.locator(".divide-y > div");
		if ((await builderRows.count()) > 1) {
			const secondBuilderRow = builderRows.nth(1);
			const bClassName = await secondBuilderRow.getAttribute("class");
			expect(bClassName).toMatch(/bg-muted/);
		}

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
