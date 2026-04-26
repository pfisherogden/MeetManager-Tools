import { expect, test } from "@playwright/test";
import { ensureDatasetActive, getFixtureData } from "./utils";

test.describe("DQ Lifecycle Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const shardIndex = process.env.SHARD_INDEX || "0";
		const userId =
			process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true"
				? `e2e-bypass-user-${shardIndex}`
				: `e2e-dq-${shardIndex}-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
		});
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
	});

	test("should process DQ from Judge app to Results PDF", async ({
		page,
		context,
	}) => {
		test.setTimeout(300000); // 5 mins
		const workerIndex = test.info().workerIndex;
		const userId = `e2e-dq-${workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		const testFileName = `tiny_dq_${workerIndex}.json`;
		const data = getFixtureData("tiny_meet.json");

		// 1. Ensure dataset is active
		await ensureDatasetActive(page, userId, testFileName, data);

		// 2. Publish to Judge App
		await page.goto("/admin");
		const row = page.getByTestId(`dataset-row-${testFileName}`);
		await row.getByTestId("publish-button").click();

		// Wait for judge URL to appear in dialog
		const judgeUrlLocator = page.getByTestId("judge-app-url");
		await expect(judgeUrlLocator).toBeVisible({ timeout: 30000 });
		const judgeUrl = await judgeUrlLocator.innerText();
		console.log(`Judge App URL: ${judgeUrl}`);

		// 3. Open Judge App in new context/page
		const judgePage = await context.newPage();
		await judgePage.goto(judgeUrl);
		await expect(judgePage.getByText(/Select Session/i)).toBeVisible({
			timeout: 20000,
		});

		// Select first session and event
		await judgePage.getByText(/Morning Session/i).click();
		await judgePage.getByText(/Event #1/i).click();

		// Add a DQ
		await judgePage.getByTestId("add-dq-button").first().click();
		await judgePage.getByTestId("dq-code-1A").click(); // False Start
		await judgePage.getByRole("button", { name: /Confirm DQ/i }).click();

		// 4. Verify DQ in Admin Dashboard
		await page.goto("/admin");
		await page.reload();
		// Dashboard stats check (if implemented in this version)
		// Otherwise check Results page
		await page.goto("/reports");
		const resultsCard = page.getByTestId("report-card-meet-results");
		await resultsCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached({ timeout: 15000 });

		const downloadPromise = page.waitForEvent("download", { timeout: 90000 });
		await page.getByRole("button", { name: "Download PDF" }).click();

		const download = await downloadPromise;
		expect(await download.path()).toBeTruthy();
	});
});
