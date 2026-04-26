import { expect, test } from "@playwright/test";
import { ensureDatasetActive, getFixtureData } from "./utils";

test.describe("Champs Dataset Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const shardIndex = process.env.SHARD_INDEX || "0";
		const userId = `e2e-champs-${shardIndex}-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
		});
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
	});

	test("should correctly process and display tiny Champs dataset", async ({
		page,
	}) => {
		test.setTimeout(300000); // 5 mins
		const shardIndex = process.env.SHARD_INDEX || "0";
		const workerIndex = test.info().workerIndex;
		const userId = `e2e-champs-${shardIndex}-${workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		const testFileName = `tiny_champs_${workerIndex}.json`;
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

		// 4. Reports Page: Generate bundle
		await page.goto("/reports", { waitUntil: "networkidle" });

		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.scrollIntoViewIfNeeded();
		await clubCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached({ timeout: 15000 });

		// Add 2 reports to pack
		for (let i = 0; i < 2; i++) {
			const addBtn = page.getByRole("button", { name: /Add to Pack/i });
			await addBtn.scrollIntoViewIfNeeded();
			await addBtn.click();
			// No toast check needed, just wait for React cycle
			await page.waitForTimeout(500);
		}

		const generateZipBtn = page.getByTestId("generate-bundle-button");
		await expect(generateZipBtn).toBeEnabled({ timeout: 10000 });

		const downloadPromise = page.waitForEvent("download", { timeout: 180000 });
		await generateZipBtn.click();

		// Wait for bundle generation to finish via state attribute
		await expect(configCard).toHaveAttribute("data-report-status", "idle", {
			timeout: 180000,
		});

		const download = await downloadPromise;
		expect(await download.path()).toBeTruthy();
	});
});
