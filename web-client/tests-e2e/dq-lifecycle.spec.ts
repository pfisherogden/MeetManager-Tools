import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	robustClick,
	waitForJudgeApp,
} from "./utils";

test.describe("DQ Lifecycle Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo, page);
		await page.setExtraHTTPHeaders({ "x-user-id": userId });
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
	});

	test("should process DQ from Judge app to Results PDF", async ({
		page,
		context,
	}, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const { getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("dq_lifecycle.json");
		const data = getFixtureData("tiny_meet.json");

		// 1. Ensure dataset is active
		await ensureDatasetActive(page, testInfo, testFileName, data);

		// 2. Publish to Judge App
		await page.goto("/admin", { waitUntil: "networkidle" });
		const row = page.getByTestId(`dataset-row-${testFileName}`);
		await row.getByTestId("publish-button").click();

		// Wait for judge URL to appear in dialog
		const judgeUrlLocator = page.getByTestId("judge-app-url");
		await expect(judgeUrlLocator).toBeVisible({ timeout: 30000 });
		let judgeUrl = (await judgeUrlLocator.textContent()) || "";

		// Align E2E URL Logic
		const frontendUrl = process.env.FRONTEND_URL || "http://localhost:3100";
		judgeUrl = judgeUrl.replaceAll("http://localhost:3000", frontendUrl);
		console.log(`Judge App URL: ${judgeUrl}`);

		// 3. Open Judge App in new context/page
		const judgePage = await context.newPage();
		await judgePage.goto(judgeUrl);
		await waitForJudgeApp(judgePage);

		await judgePage.getByPlaceholder("Your Name").fill("E2E Judge");
		await robustClick(judgePage.getByText(/START JUDGING/i));

		// Select first event directly (Event 13 from tiny_meet.json)
		await judgePage.getByTestId("event-item-13").click();

		// 3.5 Heat List: Select Heat
		await expect(judgePage.getByText(/Heat 1/i)).toBeVisible({
			timeout: 15000,
		});
		await judgePage.getByText(/Heat 1/i).click();

		// Add a DQ
		await judgePage.getByTestId("add-dq-button").first().click();

		// Select a DQ code (e.g., "1A") via new data-testid
		const code1A_selector = "[data-testid='dq-code-1A']";
		await judgePage.waitForSelector(code1A_selector, {
			state: "attached",
			timeout: 10000,
		});

		// Use evaluate click for Safari robustness
		await judgePage.evaluate((sel) => {
			const el = document.querySelector(sel);
			if (el) (el as HTMLElement).click();
		}, code1A_selector);

		// Setup sync response promise BEFORE clicking save
		const syncResponsePromise = judgePage.waitForResponse(
			(response) =>
				response.url().includes("/api/sync-dqs") && response.status() === 200,
			{ timeout: 30000 },
		);

		await judgePage.getByLabel("Save changes").click();

		// 4. Sync Data
		await syncResponsePromise;
		const syncBtn = judgePage.getByTestId("dq-history-button");
		await expect(syncBtn).toBeVisible({ timeout: 15000 });
		await syncBtn.click();

		await expect(judgePage.getByText("DQ History (Pending: 0)")).toBeVisible({
			timeout: 60000,
		});

		// 5. Verify DQ in Admin Dashboard
		await page.bringToFront();
		await page.goto("/reports", { waitUntil: "networkidle" });
		const resultsCard = page.getByTestId("report-card-meet-results");
		await resultsCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeVisible({ timeout: 15000 });

		const downloadPromise = page.waitForEvent("download", { timeout: 90000 });
		await page.getByTestId("generate-report-button").click();

		const download = await downloadPromise;
		expect(await download.path()).toBeTruthy();
	});
});
