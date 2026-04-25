import * as fs from "node:fs";
import * as path from "node:path";
import { expect, test } from "@playwright/test";

// Helper to ensure dataset is present and active
async function ensureDataset(page, _userId, filename, data) {
	await page.goto("/admin", { waitUntil: "networkidle" });
	const rowId = `dataset-row-${filename}`;
	const isPresent = (await page.getByTestId(rowId).count()) > 0;

	if (!isPresent) {
		const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
		if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
		const testFilePath = path.join(tempDir, filename);
		fs.writeFileSync(testFilePath, JSON.stringify(data));
		await page.setInputFiles('input[type="file"]', testFilePath);
		await page.getByText(/Upload Dataset/i).click();
		await expect(page.getByTestId(rowId)).toBeVisible({ timeout: 45000 });
	}

	const row = page.getByTestId(rowId);
	await row.scrollIntoViewIfNeeded();
	await row.evaluate((el) => {
		const btn = el.querySelector('button[aria-label*="Set Active"]');
		if (btn) (btn as HTMLElement).click();
	});
	await expect(row.getByTestId("active-dataset-badge")).toBeVisible({
		timeout: 15000,
	});
}

test.describe("Coach Persona Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const userId = `e2e-coach-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
		});
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);

		const testFileName = "tiny_champs.json";
		const data = JSON.parse(
			fs.readFileSync(
				path.resolve(process.cwd(), "..", "tests", "fixtures", testFileName),
				"utf8",
			),
		);
		await ensureDataset(page, userId, testFileName, data);
	});

	test("should filter reports and entries by team", async ({ page }) => {
		// 1. Verify Team Dashboard
		await page.goto("/teams");
		await expect(page.locator("table")).toContainText("Blue Dolphins");

		// 2. Go to Reports and filter by "Blue Dolphins"
		await page.goto("/reports");

		// Select Club Style report
		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.scrollIntoViewIfNeeded();
		await clubCard.evaluate((el) => (el as HTMLElement).click());

		// Wait for config card
		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached({ timeout: 15000 });

		// Open Team Filter Popover
		const teamFilterBtn = configCard
			.getByRole("combobox")
			.filter({ hasText: /All Teams/i });
		await teamFilterBtn.scrollIntoViewIfNeeded();
		await teamFilterBtn.click();

		// Select Blue Dolphins
		await page.getByRole("option", { name: "Blue Dolphins" }).click();

		// Verify summary reflects team
		const summary = page.locator("div").filter({ hasText: /^Summary/ });
		await expect(summary).toContainText("Target: Blue Dolphins");

		// 3. Add to pack and verify
		await page.getByRole("button", { name: /Add to Pack/i }).click();
		await expect(page.getByText(/Added to custom pack/i).first()).toBeVisible();

		const builder = page.locator("#report-builder");
		await expect(builder).toContainText("Blue Dolphins");

		// 4. Verification: Switching to another team updates summary
		await teamFilterBtn.click();
		await page.getByRole("option", { name: "Red Sharks" }).click();
		await expect(summary).toContainText("Target: Red Sharks");
	});
});
