import { expect, test } from "@playwright/test";
import {
	getE2ETestContext,
	mockGoogleDrivePicker,
	setupE2ESession,
} from "./utils";

/**
 * Production Validation Suite
 *
 * These tests are intended to run against a live production environment (e.g., Cloud Run).
 * They verify that the main application is up, authenticated, and can load data.
 */

test.describe("Production Smoke Tests", () => {
	test.beforeEach(async ({ page }, testInfo) => {
		await setupE2ESession(page, testInfo);
	});

	test("should load dashboard", async ({ page }) => {
		await page.goto("/");
		await expect(page.getByRole("main")).toBeVisible();
		// The app shell has "SwimMeet Pro" in the sidebar/header
		await expect(page.locator("body")).toContainText("SwimMeet Pro");
	});

	test("should load meets page", async ({ page }) => {
		await page.goto("/meets");
		await expect(page.getByRole("heading", { name: /Meets/i })).toBeVisible();
	});

	test("should load reports page", async ({ page }) => {
		await page.goto("/reports");
		await expect(page.getByRole("heading", { name: /Reports/i })).toBeVisible();
		// Check for report presets list
		await expect(page.getByText(/Default Meet Pack/i)).toBeVisible();
	});

	test("should load admin/ingestion page", async ({ page }) => {
		await page.goto("/admin");
		await expect(page.getByText(/Dataset Management/i).first()).toBeVisible();
		// Verify action buttons exist
		await expect(
			page.getByRole("button", { name: /Publish to Judge App/i }).first(),
		).toBeVisible();
	});

	test("should allow choosing a Google Drive file, uploading it, and viewing the meet", async ({
		page,
	}, testInfo) => {
		const { getFilename } = getE2ETestContext(testInfo);
		const driveFileName = getFilename("prod-drive-meet.json");
		const driveMeetData = {
			meet: [
				{
					meet_name1: "Cloud Run Drive Meet",
					meet_location: "Cloud Pool",
					meet_start: "2025-08-01",
					meet_end: "2025-08-01",
				},
			],
			team: [{ team_no: 1, team_abbr: "CLD", team_name: "Cloud Swim Team" }],
			athlete: [
				{
					ath_no: 1,
					team_no: 1,
					first_name: "Cloud",
					last_name: "Swimmer",
					sex: "M",
					ath_age: 11,
				},
			],
			event: [
				{
					event_no: 1,
					event_ptr: 1,
					event_gender: "M",
					event_dist: 50,
					event_stroke: "A",
					event_sex: "Boys",
					low_age: 11,
					high_age: 12,
					ind_rel: "I",
				},
			],
			session: [
				{
					sess_ptr: 1,
					sess_no: 1,
					sess_name: "Session 1",
					sess_day: 1,
					sess_starttime: 32400,
				},
			],
			sessitem: [{ sess_ptr: 1, event_ptr: 1, sess_order: 1, sess_rnd: "F" }],
			entry: [
				{
					ath_no: 1,
					event_ptr: 1,
					pre_heat: 1,
					pre_lane: 1,
					convseed_time: 29.1,
				},
			],
		};

		const { driveDownloadRequests } = await mockGoogleDrivePicker(page, {
			id: "cloud-drive-file-999",
			name: driveFileName,
			mimeType: "application/json",
			content: driveMeetData,
		});

		await page.goto("/admin");
		const importDriveBtn = page.getByRole("button", {
			name: /Import from Drive/i,
		});
		await expect(importDriveBtn).toBeVisible();
		await expect(importDriveBtn).toBeEnabled({ timeout: 15000 });
		await importDriveBtn.click();

		await expect(
			page.getByText(`Successfully imported ${driveFileName} from Drive`),
		).toBeVisible({ timeout: 30000 });

		expect(driveDownloadRequests.length).toBeGreaterThan(0);

		const row = page.getByTestId(`dataset-row-${driveFileName}`);
		await expect(row).toBeVisible({ timeout: 15000 });
		await expect(row).toHaveAttribute("data-test-state", "active", {
			timeout: 15000,
		});

		await page.goto("/meets");
		await expect(page.locator("table")).toContainText("Cloud Run Drive Meet", {
			timeout: 20000,
		});
	});
});
