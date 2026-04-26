import { expect, test } from "@playwright/test";
import { ensureDatasetActive, getFixtureData } from "./utils";

test.describe("Meet Administrator Management", () => {
	test.describe.configure({ mode: "serial" });

	test.beforeEach(async ({ page, context }, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const shardIndex = process.env.SHARD_INDEX || "0";
		const userId =
			process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true"
				? `e2e-bypass-user-${shardIndex}`
				: `e2e-admin-${shardIndex}-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
		});
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
		console.log(`Using isolated Admin User ID: ${userId}`);
	});

	test("should support uploading, switching between, and deleting multiple datasets", async ({
		page,
	}) => {
		const shardIndex = process.env.SHARD_INDEX || "0";
		const workerIndex = test.info().workerIndex;
		const userId =
			process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true"
				? `e2e-bypass-user-${shardIndex}`
				: `e2e-admin-${shardIndex}-${workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		const ds1 = `tiny_meet_${workerIndex}.json`;
		const ds2 = `tiny_champs_${workerIndex}.json`;

		const datasets = [
			{
				filename: ds1,
				data: getFixtureData("tiny_meet.json"),
				name: "Tiny Meet",
			},
			{
				filename: ds2,
				data: getFixtureData("tiny_champs.json"),
				name: "TVSL Championship Meet",
			},
		];

		// 1. Ensure both datasets are present
		await ensureDatasetActive(page, userId, ds1, datasets[0].data);
		await ensureDatasetActive(page, userId, ds2, datasets[1].data);

		// 2. Verify DS2 is currently active
		await page.goto("/meets");
		await expect(page.locator("table")).toContainText(
			"TVSL Championship Meet 2025",
			{ timeout: 20000 },
		);

		// 3. Switch back to ds1 and verify
		await ensureDatasetActive(page, userId, ds1, datasets[0].data);
		await page.goto("/meets");
		await expect(page.locator("table")).toContainText("Summer Meet 2024", {
			timeout: 20000,
		});

		// 4. Delete a dataset
		await page.goto("/admin", { waitUntil: "networkidle" });
		const rowToDelete = page.getByTestId(`dataset-row-${ds2}`);
		await rowToDelete.scrollIntoViewIfNeeded();

		page.once("dialog", (dialog) => dialog.accept());
		await rowToDelete.getByTestId("delete-dataset-button").click();

		await expect(page.getByTestId(`dataset-row-${ds2}`)).not.toBeVisible({
			timeout: 20000,
		});
		console.log("Dataset deleted successfully");
	});
});
