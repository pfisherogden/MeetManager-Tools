import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	robustClick,
	setupE2ESession,
} from "./utils";

test.describe("Coach Persona Journey", () => {
	test.describe.configure({ mode: "serial" });

	test.beforeEach(async ({ page }, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const { getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("tiny_champs.json");
		const data = getFixtureData("tiny_champs.json");
		await setupE2ESession(page, testInfo);
		await ensureDatasetActive(page, testInfo, testFileName, data);
	});

	test("should filter reports and entries by team", async ({ page }) => {
		// 1. Verify Team Dashboard
		await page.goto("/teams");
		await expect(page.locator("table")).toContainText(/Blue Dolphins/i, {
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
		const teamFilterBtn = configCard.getByTestId("team-filter-trigger");
		await robustClick(teamFilterBtn);

		// Select Blue Dolphins (which is in tiny_champs.json)
		// Use a more resilient approach to click the option
		const briarhillOption = page.getByRole("option", {
			name: /Blue Dolphins/i,
		});
		await expect(briarhillOption).toBeVisible({ timeout: 10000 });
		await briarhillOption.click();

		// Verify summary reflects team
		const summary = page.locator("div").filter({ hasText: /^Summary/ });
		await expect(summary).toContainText(/Target: Blue Dolphins/i, {
			timeout: 10000,
		});

		// 3. Add to pack and verify
		await page.getByRole("button", { name: /Add to Pack/i }).click();
		// No toast check - verify side effect in builder
		await page.waitForTimeout(1000); // Allow list to update

		const builder = page.locator("#report-builder");
		await expect(builder).toContainText(/Blue Dolphins/i, { timeout: 15000 });

		// 4. Verification: Switching to another team updates summary
		await page.waitForTimeout(2000);
		await teamFilterBtn.click({ force: true });

		// Select Red Sharks (another team in tiny_champs.json)
		const otherOption = page.getByRole("option", { name: /Red Sharks/i });
		await expect(otherOption).toBeVisible({ timeout: 10000 });
		await otherOption.click();

		await expect(summary).toContainText(/Target: Red Sharks/i, {
			timeout: 15000,
		});
	});
});
