import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
} from "./utils";

test.describe("Coach Persona Journey", () => {
	test.describe.configure({ mode: "serial" });

	test.beforeEach(async ({ page, context }, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const { userId, getFilename } = getE2ETestContext(testInfo, page);
		await page.setExtraHTTPHeaders({ "x-user-id": userId });
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);

		const testFileName = getFilename("tiny_champs.json");
		const data = getFixtureData("tiny_champs.json");
		await ensureDatasetActive(page, userId, testFileName, data);
	});

	test("should filter reports and entries by team", async ({ page }) => {
		// 1. Verify Team Dashboard
		await page.goto("/teams");
		await expect(page.locator("table")).toContainText("Blue Dolphins", {
			timeout: 20000,
		});

		// 2. Go to Reports and filter by "Blue Dolphins"
		await page.goto("/reports");

		// Select Club Style report
		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await robustClick(clubCard);

		// Wait for config card
		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached({ timeout: 15000 });

		// Open Team Filter Popover
		const teamFilterBtn = configCard
			.getByRole("combobox")
			.filter({ hasText: /All Teams/i });
		await robustClick(teamFilterBtn, { waitForState: "closed" });

		// Select Kyleton Swimmers (since that's in tiny_meet.json)
		await page.getByRole("option", { name: "Kyleton Swimmers" }).click();

		// Verify summary reflects team
		const summary = page.locator("div").filter({ hasText: /^Summary/ });
		await expect(summary).toContainText("Target: Kyleton Swimmers", {
			timeout: 10000,
		});

		// 3. Add to pack and verify
		await page.getByRole("button", { name: /Add to Pack/i }).click();
		// No toast check - verify side effect in builder
		await page.waitForTimeout(1000); // Allow list to update

		const builder = page.locator("#report-builder");
		await expect(builder).toContainText("Blue Dolphins", { timeout: 15000 });

		// 4. Verification: Switching to another team updates summary
		await teamFilterBtn.click();
		await page.getByRole("option", { name: "Red Sharks" }).click();
		await expect(summary).toContainText("Target: Red Sharks", {
			timeout: 15000,
		});
	});
});
