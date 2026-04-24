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

test.describe("Meet Administrator Management", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
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
		const datasets = [
			{
				filename: "tiny_meet.json",
				data: getTestData("tiny_meet.json"),
				name: "Tiny Meet",
			},
			{
				filename: "tiny_champs.json",
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
			await expect(page.getByTestId(rowId)).toBeVisible({ timeout: 30000 });
		}

		// 2. Switch to TVSL Championship and verify
		console.log("Switching to TVSL Championship...");
		const champsRow = page.getByTestId("dataset-row-tiny_champs.json");
		await champsRow.scrollIntoViewIfNeeded();
		await champsRow.evaluate((el) => {
			const btn = el.querySelector('button[aria-label*="Set Active"]');
			if (btn) (btn as HTMLElement).click();
		});
		await expect(champsRow.getByTestId("active-dataset-badge")).toBeVisible({
			timeout: 15000,
		});

		await page.goto("/meets");
		await expect(page.locator("table")).toContainText(
			"TVSL Championship Meet 2025",
		);

		// 3. Switch to Tiny Meet and verify
		console.log("Switching back to Tiny Meet...");
		await page.goto("/admin");
		const tinyRow = page.getByTestId("dataset-row-tiny_meet.json");
		await tinyRow.scrollIntoViewIfNeeded();
		await tinyRow.evaluate((el) => {
			const btn = el.querySelector('button[aria-label*="Set Active"]');
			if (btn) (btn as HTMLElement).click();
		});
		await expect(tinyRow.getByTestId("active-dataset-badge")).toBeVisible({
			timeout: 15000,
		});

		await page.goto("/meets");
		await expect(page.locator("table")).toContainText("Summer Meet 2024");

		// 4. Delete a dataset
		console.log("Deleting TVSL Championship dataset...");
		await page.goto("/admin");
		const champsRowToDelete = page.getByTestId("dataset-row-tiny_champs.json");
		await champsRowToDelete.scrollIntoViewIfNeeded();

		// Setup dialog handler for delete confirmation
		page.once("dialog", (dialog) => dialog.accept());

		await champsRowToDelete.evaluate((el) => {
			const btn = el.querySelector('button[aria-label*="Delete"]');
			if (btn) (btn as HTMLElement).click();
		});

		await expect(
			page.getByTestId("dataset-row-tiny_champs.json"),
		).not.toBeVisible({ timeout: 15000 });
		console.log("Dataset deleted successfully");
	});
});
