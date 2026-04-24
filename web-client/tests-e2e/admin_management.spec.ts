import * as fs from "node:fs";
import * as path from "node:path";
import { expect, test } from "@playwright/test";

// Helper to get raw data for upload
function getTestData(filename: string) {
	return JSON.parse(
		fs.readFileSync(
			path.resolve(process.cwd(), "..", "tests", "fixtures", filename),
			"utf8",
		),
	);
}

// Helper to ensure dataset is active using robust data attributes
async function ensureActive(page, filename) {
	console.log(`Ensuring ${filename} is active...`);

	// Force reload to get fresh state from backend
	await page.reload({ waitUntil: "networkidle" });

	const row = page.getByTestId(`dataset-row-${filename}`);
	await expect(row).toBeVisible({ timeout: 20000 });

	// Check state via data-attribute
	const state = await row.getAttribute("data-test-state");
	if (state === "active") {
		console.log(`${filename} is already active.`);
		return;
	}

	await row.scrollIntoViewIfNeeded();
	const setActiveBtn = row.getByTestId("set-active-button");
	await expect(setActiveBtn).toBeVisible({ timeout: 15000 });

	await setActiveBtn.click();

	// Wait for attribute change - MUCH more robust than CSS badge visibility
	await expect(row).toHaveAttribute("data-test-state", "active", {
		timeout: 30000,
	});
	console.log(`${filename} is now active.`);
}

test.describe("Meet Administrator Management", () => {
	test.describe.configure({ mode: "serial" });

	test.beforeEach(async ({ page, context }, testInfo) => {
		test.setTimeout(300000); // 5 mins
		const userId = `e2e-admin-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
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
		const workerIndex = test.info().workerIndex;
		const ds1 = `tiny_meet_${workerIndex}.json`;
		const ds2 = `tiny_champs_${workerIndex}.json`;

		const datasets = [
			{ filename: ds1, data: getTestData("tiny_meet.json"), name: "Tiny Meet" },
			{
				filename: ds2,
				data: getTestData("tiny_champs.json"),
				name: "TVSL Championship Meet",
			},
		];

		await page.goto("/admin", { waitUntil: "networkidle" });

		// 1. Upload both datasets
		for (const ds of datasets) {
			console.log(`Uploading ${ds.filename}...`);
			const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
			if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
			const testFilePath = path.join(tempDir, ds.filename);
			fs.writeFileSync(testFilePath, JSON.stringify(ds.data));

			await page.setInputFiles('input[type="file"]', testFilePath);
			await page.getByText(/Upload Dataset/i).click();

			const rowId = `dataset-row-${ds.filename}`;
			await expect(page.getByTestId(rowId)).toBeVisible({ timeout: 60000 });
		}

		// 2. Switch to ds2 and verify
		console.log(`Step 2: Switching to ${ds2}...`);
		await ensureActive(page, ds2);

		await page.goto("/meets");
		await expect(page.locator("table")).toContainText(
			"TVSL Championship Meet 2025",
			{ timeout: 20000 },
		);

		// 3. Switch back to ds1 and verify
		console.log(`Step 3: Switching back to ${ds1}...`);
		await page.goto("/admin");
		await ensureActive(page, ds1);

		await page.goto("/meets");
		await expect(page.locator("table")).toContainText("Summer Meet 2024", {
			timeout: 20000,
		});

		// 4. Delete a dataset
		console.log(`Step 4: Deleting ${ds2} dataset...`);
		await page.goto("/admin");
		await page.reload({ waitUntil: "networkidle" });

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
