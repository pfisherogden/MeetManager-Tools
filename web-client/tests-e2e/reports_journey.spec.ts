import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	robustClick,
	setupE2ESession,
} from "./utils";

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page }, testInfo) => {
		const { getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("tiny_meet.json");
		const data = getFixtureData("tiny_meet.json");
		await setupE2ESession(page, testInfo);
		await ensureDatasetActive(page, testInfo, testFileName, data);
	});

	test("should generate and download a ZIP bundle asynchronously", async ({
		page,
	}) => {
		test.setTimeout(480000); // 8 minutes for this test

		// Navigate to reports and select a report type to make the config card visible
		await page.goto("/reports");
		const resultsCard = page.getByTestId("report-card-meet-results");
		await resultsCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeVisible();

		// Add to pack first
		await page.getByRole("button", { name: /Add to Pack/i }).click();

		// Click the Generate ZIP button (located in the builder card)
		const builderCard = page.getByTestId("report-builder-card");
		const generateBtn = builderCard.getByTestId("generate-bundle-button");
		await robustClick(generateBtn);

		// Assert the bundling state
		await expect(builderCard).toHaveAttribute(
			"data-report-status",
			"bundling",
			{
				timeout: 30000,
			},
		);

		// Wait for progress to start moving
		await expect(async () => {
			const progressStr = await builderCard.getAttribute("data-job-progress");
			const progress = Number.parseFloat(progressStr || "0");
			expect(progress).toBeGreaterThanOrEqual(0);
		}).toPass({ timeout: 20000 });

		// Wait for completion and download
		const downloadPromise = page.waitForEvent("download", { timeout: 360000 });

		// We first wait for the status to return to 'idle' with a very long timeout
		await expect(builderCard).toHaveAttribute("data-report-status", "idle", {
			timeout: 360000, // 6 minutes for very large bundles
		});

		// Once idle, the download should have been triggered
		const download = await downloadPromise;
		expect(await download.path()).toBeTruthy();
	});
});
