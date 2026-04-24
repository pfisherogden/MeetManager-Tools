import * as fs from "node:fs";
import * as path from "node:path";
import { expect, test } from "@playwright/test";

// Helper to ensure dataset is active for screenshots
async function ensureDataset(page, _userId, filename, data) {
	await page.goto("/admin", { waitUntil: "networkidle" });
	const rowId = `dataset-row-${filename}`;
	const isPresent = (await page.getByTestId(rowId).count()) > 0;

	if (!isPresent) {
		const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
		if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
		const testFilePath = path.join(tempDir, filename);
		fs.writeFileSync(testFilePath, JSON.stringify(data));
		await page.setInputFiles('input[type="file"]', testFilePath);
		await page.getByText(/Upload Dataset/i).click();
		await expect(page.getByTestId(rowId)).toBeVisible({ timeout: 45000 });
	}

	const row = page.getByTestId(rowId);
	await row.scrollIntoViewIfNeeded();
	await row.evaluate((el) => {
		const btn = el.querySelector('button[aria-label*="Set Active"]');
		if (btn) (btn as HTMLElement).click();
	});
	await expect(row.getByTestId("active-dataset-badge")).toBeVisible({
		timeout: 15000,
	});
}

test.describe("Visual Journey Capture", () => {
	const reportDir = path.join(process.cwd(), "tmp", "visual-report");

	test.beforeEach(async ({ page, context }) => {
		const userId = "visual-capture-user";
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
		});
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);

		const testFileName = "tiny_champs.json";
		const data = JSON.parse(
			fs.readFileSync(
				path.resolve(process.cwd(), "..", "tests", "fixtures", testFileName),
				"utf8",
			),
		);
		await ensureDataset(page, userId, testFileName, data);
	});

	test("capture admin dashboard", async ({ page }) => {
		await page.goto("/admin");
		await expect(page.getByText(/Admin Configuration/i)).toBeVisible();
		await page.screenshot({
			path: path.join(reportDir, "1-admin-dashboard.png"),
			fullPage: true,
		});
		console.log("Captured: 1-admin-dashboard.png");
	});

	test("capture coach filtered reports", async ({ page }) => {
		await page.goto("/reports");
		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.evaluate((el) => (el as HTMLElement).click());

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached();

		// Filter for Blue Dolphins
		await configCard
			.getByRole("combobox")
			.filter({ hasText: /All Teams/i })
			.click();
		await page.getByRole("option", { name: "Blue Dolphins" }).click();

		await page.screenshot({
			path: path.join(reportDir, "2-coach-filtered-report.png"),
			fullPage: true,
		});
		console.log("Captured: 2-coach-filtered-report.png");
	});

	test("capture judge app events", async ({ page }) => {
		await page.goto(
			"http://localhost:8080/MeetManager-Tools/judge?uid=visual-capture-user",
		);
		await page.getByPlaceholder("Your Name").fill("Visual Reviewer");
		await page.getByText("START JUDGING").click();

		await expect(page.getByText("Events", { exact: true })).toBeVisible();
		await page.screenshot({
			path: path.join(reportDir, "3-judge-events.png"),
			fullPage: true,
		});
		console.log("Captured: 3-judge-events.png");
	});
});
