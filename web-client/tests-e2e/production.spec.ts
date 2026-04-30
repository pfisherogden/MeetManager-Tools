import { expect, test } from "@playwright/test";
import { setupE2ESession } from "./utils";

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
});
