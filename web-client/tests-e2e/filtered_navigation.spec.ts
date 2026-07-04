import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	setupE2ESession,
} from "./utils";

test.describe("Filtered Navigation", () => {
	test.beforeEach(async ({ page }, testInfo) => {
		const { getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("tiny_meet.json");
		const data = getFixtureData("tiny_meet.json");
		await setupE2ESession(page, testInfo);
		await ensureDatasetActive(page, testInfo, testFileName, data);
	});

	test("should navigate from Events to filtered Entries", async ({ page }) => {
		await page.goto("/events");

		// Event 17 is an individual event.
		const row = page
			.getByRole("row")
			.filter({ has: page.getByRole("cell", { name: "17", exact: true }) });
		const entriesLink = row.getByRole("link", { name: /View/i }).first();

		await expect(entriesLink).toBeVisible({ timeout: 15000 });
		await entriesLink.click();

		await expect(page).toHaveURL(/\/entries\/?\?event=\d+/);

		// Should show data, not "No data available"
		await expect(page.locator("table tbody tr")).not.toHaveCount(0, {
			timeout: 20000,
		});
	});

	test("should navigate from Events to filtered Relays", async ({ page }) => {
		await page.goto("/events");

		// Event 13 is a relay event.
		const row = page
			.getByRole("row")
			.filter({ has: page.getByRole("cell", { name: "13", exact: true }) });
		const relaysLink = row.getByRole("link", { name: /View/i }).first();

		await expect(relaysLink).toBeVisible({ timeout: 15000 });
		await relaysLink.click();

		await expect(page).toHaveURL(/\/relays\/?\?event=\d+/);

		// Should show data
		await expect(page.locator("table tbody tr")).not.toHaveCount(0, {
			timeout: 20000,
		});
	});

	test("should show all Entries when no filter is applied", async ({
		page,
	}) => {
		await page.goto("/entries");
		await expect(page.locator("table tbody tr")).not.toHaveCount(0, {
			timeout: 15000,
		});
	});

	test("should show all Relays when no filter is applied", async ({ page }) => {
		await page.goto("/relays");
		await expect(page.locator("table tbody tr")).not.toHaveCount(0, {
			timeout: 15000,
		});
	});
});
