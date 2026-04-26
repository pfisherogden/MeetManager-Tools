import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
} from "./utils";

test.describe("Meet Administrator Management", () => {
	test.describe.configure({ mode: "serial" });

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
		console.log(`Using isolated Admin User ID: ${userId}`);
	});

	test("should support uploading, switching between, and deleting multiple datasets", async ({
		page,
	}, testInfo) => {
		const { userId, getFilename } = getE2ETestContext(testInfo);
		const ds1 = getFilename("tiny_meet.json");
		const ds2 = getFilename("tiny_champs.json");

		const datasets = [
			{
				filename: ds1,
				fixture: "tiny_meet.json",
				expectedText: "Del Prado at Pleasanton Cup",
			},
			{
				filename: ds2,
				fixture: "tiny_champs.json",
				expectedText: "TVSL Championship Meet 2025",
			},
		];

		// 1. Upload both datasets
		for (const ds of datasets) {
			const data = getFixtureData(ds.fixture);
			await ensureDatasetActive(page, userId, ds.filename, data);
		}

		// 2. Switch between them and verify /meets content
		for (const ds of datasets) {
			await page.goto("/admin");
			const row = page.getByTestId(`dataset-row-${ds.filename}`);
			const setActiveBtn = row.getByTestId("set-active-button");

			// Only click if not already active
			const state = await row.getAttribute("data-test-state");
			if (state !== "active") {
				await setActiveBtn.click();
				// Wait for revalidation
				await page.waitForTimeout(2000);
			}

			// Verify meets page
			await page.goto("/meets", { waitUntil: "networkidle" });
			await expect(page.locator("table")).toContainText(ds.expectedText, {
				timeout: 20000,
			});
		}

		// 3. Delete a dataset
		await page.goto("/admin");
		const deleteDs = datasets[0];
		const deleteRow = page.getByTestId(`dataset-row-${deleteDs.filename}`);
		const deleteBtn = deleteRow.getByTestId("delete-dataset-button");

		// Handle confirmation dialog if present (assuming standard browser confirm for now or custom UI)
		page.on("dialog", (dialog) => dialog.accept());
		await deleteBtn.click();

		// Verify row is gone
		await expect(deleteRow).not.toBeVisible({ timeout: 10000 });
	});
});
