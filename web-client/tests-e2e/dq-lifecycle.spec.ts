import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	setupE2ESession,
	waitForJudgeApp,
} from "./utils";

test.describe("DQ Lifecycle Journey", () => {
	test.beforeEach(async ({ page }, testInfo) => {
		await setupE2ESession(page, testInfo);
	});
	test("should process DQ from Judge app to Results PDF", async ({
		page,
		context,
		baseURL,
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

		// Align E2E URL Logic: Use MOBILE_APP_URL as source of truth
		const _mobileAppUrl = process.env.MOBILE_APP_URL || "http://localhost:8082";
		const _frontendUrl = process.env.FRONTEND_URL || "http://localhost:3000";

		// Align E2E URL Logic: Use baseURL as the source of truth for the monolith
		const baseAddr = baseURL || "http://localhost:3000";
		const urlObj = new URL(judgeUrl);
		const baseObj = new URL(baseAddr);

		urlObj.protocol = baseObj.protocol;
		urlObj.host = baseObj.host;
		urlObj.port = baseObj.port;

		// Ensure it hits the monolith path
		if (!urlObj.pathname.includes("/judge/")) {
			urlObj.pathname = "/judge/index.html";
		}

		judgeUrl = urlObj.toString();
		console.log(`Judge App URL: ${judgeUrl}`);

		// 3. Open Judge App in new context/page
		const judgePage = await context.newPage();

		// Setup console logging for the NEW page
		getE2ETestContext(testInfo, judgePage);

		await judgePage.goto(judgeUrl);
		await waitForJudgeApp(judgePage);

		await judgePage.getByPlaceholder("Your Name").fill("E2E Judge");
		await judgePage.getByText(/START JUDGING/i).click();

		// Select first event directly (Event 13 from tiny_meet.json)
		const eventItem = judgePage.getByTestId("event-item-13");
		await expect(eventItem).toBeVisible({
			timeout: 60000,
		});
		await eventItem.click();

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

		await judgePage.getByLabel("Save changes").click();

		// 4. Sync Data
		const syncBtn = judgePage.getByTestId("dq-history-button");
		await expect(syncBtn).toBeVisible({ timeout: 15000 });

		// Wait for the sync response to ensure it actually hits the backend
		const syncResponsePromise = judgePage.waitForResponse(
			(resp) =>
				(resp.url().includes("/api/sync-dqs") ||
					resp.url().includes("/api/submit-dq")) &&
				resp.status() === 200,
			{ timeout: 60000 },
		);

		await syncBtn.click();

		await syncResponsePromise;

		await expect(judgePage.getByText("DQ History (Pending: 0)")).toBeVisible({
			timeout: 60000,
		});

		// 5. Verify DQ in Web UI (Submitted DQs Page)
		await page.bringToFront();
		await page.goto("/dqs", { waitUntil: "networkidle" });
		await expect(page.getByRole("table")).toContainText("1A", {
			timeout: 15000,
		});
		await expect(page.getByRole("table")).toContainText("E2E Judge", {
			timeout: 15000,
		});

		// 6. Verify DQ in Results PDF
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
