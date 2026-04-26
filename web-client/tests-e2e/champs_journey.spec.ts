import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
} from "./utils";

test.describe("Champs Dataset Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
		await page.setExtraHTTPHeaders({ "x-user-id": userId });
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
	});

	test("should correctly process and display tiny Champs dataset", async ({
		page,
	}, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const { userId, getFilename } = getE2ETestContext(testInfo);
		const testFileName = getFilename("tiny_champs.json");
		const data = getFixtureData("tiny_champs.json");

		// 1. Ensure dataset is active
		await ensureDatasetActive(page, userId, testFileName, data);

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
		const configCard = page.getByTestId("config-card-results");
		await expect(configCard).toBeVisible();

		// Start generation
		const generateBtn = configCard.getByTestId("generate-button");
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
