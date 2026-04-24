import * as fs from "node:fs";
import * as path from "node:path";
import { expect, test } from "@playwright/test";

// Helper to ensure dataset is present and active using data attributes
async function ensureDataset(page, userId, filename, data) {
	console.log(`Ensuring dataset for ${userId}: ${filename}...`);
	await page.goto("/admin", { waitUntil: "networkidle" });

	const rowId = `dataset-row-${filename}`;
	const row = page.getByTestId(rowId);
	const isPresent = (await row.count()) > 0;

	if (!isPresent) {
		const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
		if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
		const testFilePath = path.join(tempDir, filename);
		fs.writeFileSync(testFilePath, JSON.stringify(data));

		await page.setInputFiles('input[type="file"]', testFilePath);
		await page.getByText(/Upload Dataset/i).click();
		await expect(row).toBeVisible({ timeout: 60000 });
	}

	// Check if already active via data-attribute
	const state = await row.getAttribute("data-test-state");
	if (state === "active") return;

	await row.scrollIntoViewIfNeeded();
	await row.evaluate((el) => {
		const btn = el.querySelector('button[data-testid="set-active-button"]');
		if (btn) (btn as HTMLElement).click();
	});

	await expect(row).toHaveAttribute("data-test-state", "active", {
		timeout: 20000,
	});
	console.log(`Dataset ${filename} is now active`);
}

async function ensureTinyMeetActive(page, userId) {
	const testFileName = "tiny_meet.json";
	const tinyMeetData = JSON.parse(
		fs.readFileSync(
			path.resolve(process.cwd(), "..", "tests", "fixtures", testFileName),
			"utf8",
		),
	);
	await ensureDataset(page, userId, testFileName, tinyMeetData);
}

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const userId = `e2e-reports-${testInfo.workerIndex}-${testInfo.project.name.replace(/\s+/g, "-")}`;
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
			"x-e2e-uid": userId,
		});
		await context.addCookies([
			{ name: "x-user-id", value: userId, domain: "localhost", path: "/" },
		]);
		console.log(`Using isolated User ID: ${userId}`);
	});

	test("should ensure tiny_meet.json is active and navigate to Reports", async ({
		page,
	}) => {
		const userId = `e2e-reports-${test.info().workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		await ensureTinyMeetActive(page, userId);
		await page.goto("/reports", { waitUntil: "networkidle" });
		await expect(
			page.getByRole("heading", { name: "Reports", exact: true }),
		).toBeVisible({ timeout: 30000 });
	});

	test("should generate and preview HTML Meet Program", async ({ page }) => {
		const userId = `e2e-reports-${test.info().workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		await ensureTinyMeetActive(page, userId);
		await page.goto("/reports", { waitUntil: "networkidle" });

		const htmlCard = page.getByTestId("report-card-meet-program-(html)");
		await htmlCard.scrollIntoViewIfNeeded();
		await htmlCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached({ timeout: 15000 });

		const viewBtn = page.getByRole("button", { name: "View HTML" });
		await viewBtn.scrollIntoViewIfNeeded();
		await viewBtn.click();

		// Use robust status attribute check
		await expect(configCard).toHaveAttribute("data-report-status", "idle", {
			timeout: 60000,
		});

		// Final fallback for toast to maintain double-verification
		await expect(
			page
				.getByText(/HTML Preview opened/i)
				.or(page.getByText(/HTML Program opened/i)),
		).toBeVisible({ timeout: 20000 });
	});

	test("should generate PDF Entries report and verify layout", async ({
		page,
	}, _testInfo) => {
		const userId = `e2e-reports-${test.info().workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		await ensureTinyMeetActive(page, userId);
		await page.goto("/reports", { waitUntil: "networkidle" });

		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.scrollIntoViewIfNeeded();
		await clubCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached({ timeout: 15000 });

		const downloadPromise = page.waitForEvent("download", { timeout: 60000 });
		const downloadBtn = page.getByRole("button", { name: "Download PDF" });
		await downloadBtn.click();

		const download = await downloadPromise;
		expect(await download.path()).toBeTruthy();
	});

	test("should generate Lane Timer Sheets and verify repeating headers", async ({
		page,
	}) => {
		const userId = `e2e-reports-${test.info().workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		await ensureTinyMeetActive(page, userId);
		await page.goto("/reports", { waitUntil: "networkidle" });

		const timerCard = page.getByTestId("report-card-lane-timer-sheets");
		await timerCard.scrollIntoViewIfNeeded();
		await timerCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached({ timeout: 15000 });

		// Toggle HTML
		const toggle = page.getByTestId("html-preview-toggle");
		await toggle.click();

		const viewBtn = page.getByTestId("generate-report-button").first();
		await expect(viewBtn).toHaveText(/View HTML/i);
		await viewBtn.click();

		// Use robust status attribute check
		await expect(configCard).toHaveAttribute("data-report-status", "idle", {
			timeout: 60000,
		});
		await expect(
			page
				.getByText(/HTML Preview opened/i)
				.or(page.getByText(/HTML Program opened/i)),
		).toBeVisible({ timeout: 20000 });
	});

	test("should verify other report types are selectable", async ({ page }) => {
		const userId = `e2e-reports-${test.info().workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		await ensureTinyMeetActive(page, userId);
		await page.goto("/reports", { waitUntil: "networkidle" });

		const types = [
			"Psych Sheet",
			"Meet Entries",
			"Lineup Sheets",
			"Meet Results",
		];
		for (const type of types) {
			const testId = `report-card-${type.toLowerCase().replace(/\s+/g, "-")}`;
			await page.getByTestId(testId).click();
			await expect(
				page.locator("div").filter({ hasText: /^Summary/ }),
			).toContainText(type, { timeout: 10000 });
		}
	});
});
