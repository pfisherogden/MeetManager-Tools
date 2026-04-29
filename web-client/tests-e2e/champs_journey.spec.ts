import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
} from "./utils";

test.describe("Champs Dataset Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo, page);
		await page.setExtraHTTPHeaders({ "x-user-id": userId });
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
	});

	test("should correctly process and display tiny Champs dataset", async ({
		page,
	}, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const { getFilename } = getE2ETestContext(testInfo);
		const testFileName = getFilename("tiny_champs.json");
		const data = getFixtureData("tiny_champs.json");

		// 1. Ensure dataset is active
		await ensureDatasetActive(page, testInfo, testFileName, data);

		// 2. Meets Page: Verify name
		await page.goto("/meets", { waitUntil: "networkidle" });
		await expect(page.locator("table")).toContainText(
			"TVSL Championship Meet 2025",
			{ timeout: 20000 },
		);

		// 3. Teams Page: Verify data
		await page.goto("/teams");
		await expect(page.locator("table")).toContainText("Blue Dolphins", {
			timeout: 20000,
		});

		// 4. Reports Page: Verify generation
		await page.goto("/reports");

		// Select "Meet Results" card
		const resultsCard = page.getByTestId("report-card-meet-results");
		await expect(resultsCard).toBeVisible();
		await resultsCard.click();

		// Configure and Generate
		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeVisible();

		// Start generation
		const generateBtn = configCard.getByTestId("generate-report-button");
		await generateBtn.click();

		// Wait for completion and download
		const downloadPromise = page.waitForEvent("download");

		// Poll for finish via state attribute
		await expect(configCard).toHaveAttribute("data-report-status", "idle", {
			timeout: 180000,
		});

		const download = await downloadPromise;
		expect(await download.path()).toBeTruthy();
	});
});
