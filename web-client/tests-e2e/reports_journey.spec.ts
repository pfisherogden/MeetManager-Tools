import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
} from "./utils";

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const { userId, getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("tiny_meet.json");
		const data = getFixtureData("tiny_meet.json");
		await page.setExtraHTTPHeaders({ "x-user-id": userId });
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
		await ensureDatasetActive(page, userId, testFileName, data);
	});

	test("should generate and download a ZIP bundle asynchronously", async ({
		page,
	}) => {
		test.setTimeout(180000); // 3 minutes for this test

		// Navigate to reports and select a report type to make the config card visible
		await page.goto("/reports");
		const resultsCard = page.getByTestId("report-card-meet-results");
		await resultsCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeVisible();

		// Click the Generate ZIP button
		const generateBtn = configCard.getByTestId("generate-bundle-button");
		await robustClick(generateBtn);

		// Assert the bundling state
		await expect(configCard).toHaveAttribute("data-report-status", "bundling", {
			timeout: 30000,
		});

		// Wait for progress to start moving (optional, but good for stability)
		await expect(async () => {
			const progressStr = await configCard.getAttribute("data-job-progress");
			const progress = Number.parseFloat(progressStr || "0");
			expect(progress).toBeGreaterThanOrEqual(0);
		}).toPass({ timeout: 20000 });

		// Wait for the download to be triggered by the frontend's polling
		// We first wait for the status to return to 'idle' with a very long timeout
		await expect(configCard).toHaveAttribute("data-report-status", "idle", {
			timeout: 300000, // 5 minutes for very large bundles
		});

		// Once idle, the download should have been triggered
		const download = await downloadPromise;
		expect(await download.path()).toBeTruthy();
	});
});
