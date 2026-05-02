import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	setupE2ESession,
} from "./utils";

test.describe("Publish to Judge App", () => {
	test.beforeEach(async ({ page }, testInfo) => {
		const { getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("tiny_meet.json");
		const data = getFixtureData("tiny_meet.json");
		await setupE2ESession(page, testInfo);
		await ensureDatasetActive(page, testInfo, testFileName, data);
	});

	test("should publish meet data and generate valid URLs with tokens", async ({
		page,
	}) => {
		await page.goto("/admin");

		// Find the Publish button specifically for our active dataset
		const row = page.locator(`[data-testid*="dataset-row-tiny_meet"]`);
		const publishBtn = row.getByTestId("publish-button");
		await expect(publishBtn).toBeVisible();

		// Capture the network request/response
		const _publishPromise = page.waitForResponse(
			(r) =>
				r.url().includes("/api/publish") ||
				(r.request().method() === "POST" && r.url().includes("/admin")),
			{ timeout: 30000 },
		);

		await publishBtn.click();

		// Wait for success toast or message
		await expect(page.locator("body")).toContainText(
			/Meet data published to Judge App/i,
			{ timeout: 30000 },
		);

		// Check if the generated URL is visible and valid
		const urlInput = page.getByTestId("judge-app-url");
		await expect(urlInput).toBeVisible();
		const generatedUrl = await urlInput.innerText();
		console.log(`Generated Judge URL: ${generatedUrl}`);

		expect(generatedUrl).toContain("program_url=");
		expect(generatedUrl).toContain("sync_url=");

		// Check for encoded token in the outer URL
		expect(generatedUrl).toMatch(/token%3D[a-zA-Z0-9%+/=]+/);

		// Also verify the decoded URL
		const decodedUrl = decodeURIComponent(generatedUrl);
		console.log(`Decoded Judge URL: ${decodedUrl}`);
		expect(decodedUrl).toContain("token=");
		expect(decodedUrl).not.toContain("token=&");
	});
});
