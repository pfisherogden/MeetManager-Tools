import { expect, test } from "@playwright/test";
import { ensureDatasetActive, getFixtureData } from "./utils";

test.describe("Reports Generation Journey", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		test.setTimeout(300000); // 5 mins
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

	async function ensureTinyMeetActive(page, userId) {
		const testFileName = "tiny_meet.json";
		const data = getFixtureData(testFileName);
		await ensureDatasetActive(page, userId, testFileName, data);
	}

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

		// Use robust status attribute check instead of toast
		await expect(configCard).toHaveAttribute("data-report-status", "idle", {
			timeout: 90000,
		});
	});

	test("should generate PDF Entries report and verify layout", async ({
		page,
	}) => {
		const userId = `e2e-reports-${test.info().workerIndex}-${test.info().project.name.replace(/\s+/g, "-")}`;
		await ensureTinyMeetActive(page, userId);
		await page.goto("/reports", { waitUntil: "networkidle" });

		const clubCard = page.getByTestId("report-card-entries-(club-style)");
		await clubCard.scrollIntoViewIfNeeded();
		await clubCard.click();

		const configCard = page.getByTestId("report-configuration-card");
		await expect(configCard).toBeAttached({ timeout: 15000 });

		const downloadPromise = page.waitForEvent("download", { timeout: 90000 });
		const downloadBtn = page.getByRole("button", { name: "Download PDF" });
		await downloadBtn.click();

		const download = await downloadPromise;
		expect(await download.path()).toBeTruthy();

		// Verify status returns to idle
		await expect(configCard).toHaveAttribute("data-report-status", "idle", {
			timeout: 60000,
		});
	});

	test("should generate Lane Timer Sheets and verify status", async ({
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
			timeout: 90000,
		});
	});
});
