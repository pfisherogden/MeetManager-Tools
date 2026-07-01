import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	robustClick,
	setupE2ESession,
	waitForJudgeApp,
} from "./utils";

test.describe("Mobile Judge App Journey", () => {
	test.beforeEach(async ({ page }, testInfo) => {
		const { userId } = await setupE2ESession(page, testInfo);
		console.log(`Using isolated Judge User ID: ${userId}`);
	});
	test("should allow a judge to login, select event, and submit DQ", async ({
		page,
		context,
	}, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const { getFilename } = getE2ETestContext(testInfo);

		// 0. Setup: Upload and Publish a dataset
		const testFileName = getFilename("tiny_meet.json");
		const data = getFixtureData("tiny_meet.json");
		await ensureDatasetActive(page, testInfo, testFileName, data);

		// Now publish it
		await page.goto("/admin", { waitUntil: "networkidle" });
		const row = page.getByTestId(`dataset-row-${testFileName}`);
		await row.getByTestId("publish-button").click();

		// Wait for judge URL to appear in dialog
		const judgeUrlLocator = page.getByTestId("judge-app-url");
		await expect(judgeUrlLocator).toBeVisible({ timeout: 30000 });
		let judgeUrl = (await judgeUrlLocator.textContent()) || "";

		// Align E2E URL Logic: Use MOBILE_APP_URL as source of truth
		const _mobileAppUrl = process.env.MOBILE_APP_URL || "http://localhost:8081";
		const _frontendUrl = process.env.FRONTEND_URL || "http://localhost:3000";

		// Align E2E URL Logic: Use baseURL as the source of truth for the monolith
		const baseURL = testInfo.project.use.baseURL || "http://localhost:3100";
		const urlObj = new URL(judgeUrl);
		const baseObj = new URL(baseURL);

		urlObj.protocol = baseObj.protocol;
		urlObj.host = baseObj.host;
		urlObj.port = baseObj.port;

		// Ensure it hits the monolith path
		if (!urlObj.pathname.includes("/judge/")) {
			urlObj.pathname = "/judge/index.html";
		}

		judgeUrl = urlObj.toString();
		console.log(`Authorized Judge App URL: ${judgeUrl}`);

		// 1. Initial Page: Enter Name (on the specific authorized URL)
		const judgePage = await context.newPage();

		// Setup console logging for the NEW page
		judgePage.on("console", (msg) => {
			console.log(`[Judge App Console] [${msg.type()}] ${msg.text()}`);
		});

		await judgePage.goto(judgeUrl);
		await waitForJudgeApp(judgePage);

		await judgePage.getByPlaceholder("Your Name").fill("E2E Judge");
		await robustClick(judgePage.getByText(/START JUDGING/i));

		// 2. Meet List: Select Meet
		// Wait for meet data to be fetched from backend (auth check)
		const eventItem = judgePage.getByTestId("event-item-13");
		await expect(eventItem).toBeVisible({
			timeout: 60000,
		});
		await eventItem.click();

		// 3. Heat List: Select Heat
		await expect(judgePage.getByText(/Heat 1/i)).toBeVisible({
			timeout: 15000,
		});
		await judgePage.getByText(/Heat 1/i).click();

		// 4. Heat Detail: Click a swimmer to DQ
		// Look for "TAP TO DQ" button
		const dqBtn = judgePage.getByText(/TAP TO DQ/i).first();
		await expect(dqBtn).toBeVisible({ timeout: 15000 });
		await dqBtn.click();

		// 5. Verify DQ Modal opens
		await expect(
			judgePage.getByPlaceholder("Add notes here (optional)"),
		).toBeVisible();

		// 6. Select a DQ code (e.g., "1A") via new data-testid
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

		// 7. Add Note and Submit
		await judgePage
			.getByPlaceholder("Add notes here (optional)")
			.fill("E2E Test Note");

		// Setup sync response promise BEFORE clicking save
		const syncResponsePromise = judgePage.waitForResponse(
			(resp) =>
				(resp.url().includes("/api/sync-dqs") ||
					resp.url().includes("/api/submit-dq")) &&
				resp.status() === 200,
			{ timeout: 60000 },
		);

		await robustClick(judgePage.getByLabel("Save changes"));

		// 8. Verify submission (wait for modal to close or history to update)
		await expect(
			judgePage.getByPlaceholder("Add notes here (optional)"),
		).not.toBeVisible();

		// 9. Sync Data (Offline -> Online)
		const syncBtn = judgePage.getByTestId("dq-history-button");
		await expect(syncBtn).toBeVisible({ timeout: 15000 });

		await robustClick(syncBtn, { timeout: 30000 });

		await syncResponsePromise;

		await expect(judgePage.getByText("DQ History (Pending: 0)")).toBeVisible({
			timeout: 60000,
		});
		// Optional success message check
		const successMsg = judgePage.getByText(/Successfully synced/i);
		if (await successMsg.isVisible()) {
			console.log("Verified success message visibility");
		}

		await expect(judgePage.getByText("DQ History (Total: 1)")).toBeVisible();
	});
});
