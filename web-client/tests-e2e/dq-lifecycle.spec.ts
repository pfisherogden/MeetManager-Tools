import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
} from "./utils";

test.describe("DQ Lifecycle Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
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
		const { userId, getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("dq_lifecycle.json");
		const data = getFixtureData("tiny_meet.json");

		// 1. Ensure dataset is active
		await ensureDatasetActive(page, userId, testFileName, data);

		// 2. Publish to Judge App
		await page.goto("/admin", { waitUntil: "networkidle" });
		const row = page.getByTestId(`dataset-row-${testFileName}`);
		await row.getByTestId("publish-button").click();

		// Wait for judge URL to appear in dialog
		const judgeUrlLocator = page.getByTestId("judge-app-url");
		await expect(judgeUrlLocator).toBeVisible({ timeout: 30000 });
		let judgeUrl = (await judgeUrlLocator.textContent()) || "";

		// Dynamic port remapping for local E2E
		const frontendUrl = process.env.FRONTEND_URL || "http://localhost:3000";
		if (frontendUrl !== "http://localhost:3000") {
			console.log(`[E2E] Remapping judgeUrl from localhost:3000 to ${frontendUrl}`);
			judgeUrl = judgeUrl.replaceAll("http://localhost:3000", frontendUrl);
		}
		console.log(`Judge App URL: ${judgeUrl}`);

		// 3. Open Judge App in new context/page
		const judgePage = await context.newPage();
		
		// Setup console logging for the NEW page
		getE2ETestContext(testInfo, judgePage);
		
		await judgePage.goto(judgeUrl);

		// Wait for app to be ready (hydration sentinel)
		// We use a robust polling strategy to handle HMR/Fast Refresh noise
		console.log("[E2E] Waiting for Judge App hydration/readiness...");
		let ready = false;
		for (let i = 0; i < 30; i++) {
			try {
				const loginVisible = await judgePage.getByPlaceholder("Your Name").isVisible();
				const eventsVisible = await judgePage.getByText(/Events/i).isVisible();
				const sessionVisible = await judgePage.getByText(/Session 1/i).isVisible();
				if (loginVisible || eventsVisible || sessionVisible) {
					ready = true;
					break;
				}
			} catch (e) {}
			await judgePage.waitForTimeout(2000);
			if (i % 5 === 0 && i > 0) await judgePage.reload({ waitUntil: "networkidle" });
		}
		expect(ready).toBe(true);

		const loginVisible = await judgePage.getByPlaceholder("Your Name").isVisible();
		if (loginVisible) {
			await judgePage.getByPlaceholder("Your Name").fill("E2E Judge");
			await judgePage.getByText(/START JUDGING/i).click();
		}

		// Select first event directly (Event 13 from tiny_meet.json)
		await judgePage.getByTestId("event-item-13").click();

		// 3.5 Heat List: Select Heat
		await expect(judgePage.getByText(/Heat 1/i)).toBeVisible({ timeout: 15000 });
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
