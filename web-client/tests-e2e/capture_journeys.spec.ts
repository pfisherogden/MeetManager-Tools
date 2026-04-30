import * as path from "node:path";
import { expect, test } from "@playwright/test";
import {
	ensureDatasetActive,
	getE2ETestContext,
	getFixtureData,
	robustClick,
	setupE2ESession,
} from "./utils";

test.describe("Visual Journey Capture", () => {
	const reportDir = path.join(process.cwd(), "tmp", "visual-report");

	test.beforeEach(async ({ page }, testInfo) => {
		const { getFilename } = getE2ETestContext(testInfo, page);
		const testFileName = getFilename("tiny_champs.json");
		const data = getFixtureData("tiny_champs.json");
		await setupE2ESession(page, testInfo);
		await ensureDatasetActive(page, testInfo, testFileName, data);
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
		await robustClick(clubCard);

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

	test("capture judge app events", async ({ page }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
		const frontendUrl = process.env.FRONTEND_URL || "http://localhost:3100";
		const judgeBase =
			process.env.MOBILE_APP_URL || `${frontendUrl}/judge/index.html`;
		await page.goto(`${judgeBase}?uid=${userId}`);
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
