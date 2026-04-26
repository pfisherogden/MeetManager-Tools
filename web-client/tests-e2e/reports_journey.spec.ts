import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
} from "./utils";

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const { userId } = getE2ETestContext(testInfo);
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
		});
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
		console.log(`Using isolated User ID: ${userId}`);
	});

	async function ensureTinyMeetActive(page, userId, testInfo) {
		const { getFilename } = getE2ETestContext(testInfo);
		const testFileName = getFilename("tiny_meet.json");
		const data = getFixtureData("tiny_meet.json");
		await ensureDatasetActive(page, userId, testFileName, data);
	}

	test("should ensure tiny_meet.json is active and navigate to Reports", async ({
		page,
	}, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
		await ensureTinyMeetActive(page, userId, testInfo);
		await page.goto("/reports", { waitUntil: "networkidle" });
		await expect(
			page.getByRole("heading", { name: "Reports", exact: true }),
		).toBeVisible({ timeout: 30000 });
	});

	test("should generate Results Report", async ({ page }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
		await ensureTinyMeetActive(page, userId, testInfo);
		await page.goto("/reports", { waitUntil: "networkidle" });

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

	test("should generate Individual Awards Report", async ({
		page,
	}, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
		await ensureTinyMeetActive(page, userId, testInfo);
		await page.goto("/reports", { waitUntil: "networkidle" });

		const configCard = page.getByTestId("config-card-awards");
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
