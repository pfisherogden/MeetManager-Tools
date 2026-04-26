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

	async function ensureTinyMeetActive(
		page: any,
		userId: string,
		testInfo: any,
	) {
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

		// Select "Meet Results" card
		const resultsCard = page.getByTestId("report-card-meet-results");
		await expect(resultsCard).toBeVisible();
		await resultsCard.click();

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

	test("should generate Psych Sheet Report", async ({ page }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
		await ensureTinyMeetActive(page, userId, testInfo);
		await page.goto("/reports", { waitUntil: "networkidle" });

		// Select "Psych Sheet" card
		const psychCard = page.getByTestId("report-card-psych-sheet");
		await expect(psychCard).toBeVisible();
		await psychCard.click();

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
