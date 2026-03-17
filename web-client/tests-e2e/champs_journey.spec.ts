import * as path from "node:path";
import { expect, test } from "@playwright/test";

test.describe("Champs Dataset Journey", () => {
	test("should correctly process and display Champs 2025 dataset", async ({
		page,
	}) => {
		test.setTimeout(150000);

		// 1. Admin: Upload and Set Active
		await page.goto("/admin");
		const testFileName = "sample_data_champs_2025-aftermeet.mdb";
		// Use absolute path from project root if possible, or fallback
		const testFilePath = process.env.CI
			? path.join(process.cwd(), "..", "backend", "data", testFileName)
			: path.resolve(__dirname, `../../backend/data/${testFileName}`);

		console.log(`Using test file path: ${testFilePath}`);

		// Wait for the table to load
		await page.waitForSelector("table");

		const existingRow = page.locator("tr").filter({ hasText: testFileName });
		if ((await existingRow.count()) === 0) {
			const fileChooserPromise = page.waitForEvent("filechooser");
			await page.getByRole("button", { name: "Upload Dataset" }).click();
			const fileChooser = await fileChooserPromise;
			await fileChooser.setFiles(testFilePath);
			await expect(page.getByText("Dataset uploaded successfully")).toBeVisible(
				{ timeout: 45000 },
			);
		}

		// Set as active with retry/wait because DB loading is slow
		const datasetRow = page.locator("tr").filter({ hasText: testFileName });
		await expect(datasetRow).toBeVisible({ timeout: 10000 });

		const setActiveBtn = datasetRow.getByRole("button", { name: "Set Active" });
		const activeBadge = datasetRow.locator(".bg-green-100, .text-green-700");

		if (await activeBadge.isHidden()) {
			await setActiveBtn.click();
			// The toast might appear, but let's wait for the badge which is the source of truth
			await expect(activeBadge).toBeVisible({ timeout: 30000 });
		}

		// Verify config.json is hidden
		await expect(
			page.locator("tr").filter({ hasText: "config.json" }),
		).not.toBeVisible();

		// 2. Meets Page: Verify name and location
		await page.goto("/meets");
		await expect(page.locator("table")).toContainText(
			"TVSL Championship Meet 2025",
		);
		await expect(page.locator("table")).toContainText("Foothill High School");

		// 3. Teams Page: Verify data visibility
		await page.goto("/teams");
		await expect(page.locator("table")).toContainText("Briarhill Swim Team");
		await expect(page.locator("table")).toContainText("Del Prado Stingrays");

		// 4. Athletes Page: Verify data visibility
		await page.goto("/athletes");
		await expect(page.locator("table")).toContainText("Bertalotto"); // Evan Bertalotto

		// 5. Entries Page: Verify rounding (3 decimal places)
		await page.goto("/entries");
		// Check for times with exactly 3 digits after decimal
		// e.g. "31.240" or "1:15.720"
		const entryCells = page.locator("table tbody td");
		const cellTexts = await entryCells.allInnerTexts();
		// Use a more robust regex that allows for times like 1:23.456 and doesn't require it to be the whole cell content
		const times = cellTexts.filter((t) => t.match(/\d+\.\d{3}(\s|$)/));
		expect(times.length).toBeGreaterThan(0);
		// Ensure no 2-digit decimals in time-like cells (we now force 3)
		// We check specifically for the pattern of a swim time
		const twoDigitDecimals = cellTexts.filter((t) =>
			t.match(/^\d+:\d{2}\.\d{2}$|^\d{2}\.\d{2}$/),
		);
		expect(twoDigitDecimals.length).toBe(0);

		// 6. Events -> Relays: Verify navigation filter
		await page.goto("/events");
		const relayRow = page.locator("tr").filter({ hasText: /Relay/i }).first();
		const relayEventId = await relayRow.locator("td").first().innerText();
		await relayRow.getByRole("link", { name: "View" }).click();
		await expect(page).toHaveURL(new RegExp(`/relays\\?event=${relayEventId}`));
		await expect(page.locator("table tbody tr").first()).toBeVisible();
		// 7. Reports: Verify custom bundle generation
		await page.goto("/reports");
		await page.waitForLoadState("networkidle");

		// Select Report Type Card
		await page
			.getByRole("heading", { name: "Meet Program (PDF)", exact: true })
			.click();
		await page.getByRole("button", { name: "Add to Pack" }).click();

		// Select Lineup Sheets Card
		await page
			.getByRole("heading", { name: "Lineup Sheets", exact: true })
			.click();
		await page.getByRole("button", { name: "Add to Pack" }).click();

		// Click Generate Bundle ZIP in the Pack summary section
		const generateZipBtn = page.getByRole("button", {
			name: /Generate Bundle ZIP/i,
		});
		await expect(generateZipBtn).toBeVisible({ timeout: 20000 });
		await generateZipBtn.click();

		await expect(
			page.getByText("Bundle generated successfully", { exact: false }),
		).toBeVisible({ timeout: 60000 });
	});
});
