import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { getE2ETestContext } from "./utils";

/**
 * Production Validation Suite
 *
 * These tests are intended to run against a live production environment (e.g., Cloud Run).
 * They verify that the main application is up, authenticated, and can load data.
 */

const authFile = path.join(__dirname, "../../auth.json");

test.describe("Production Smoke Tests", () => {
	test.beforeEach(async ({ page, context }, testInfo) => {
		const { userId } = getE2ETestContext(testInfo);
		const domain = new URL(process.env.BASE_URL || "http://localhost:3000")
			.hostname;

		// If auth.json exists, we don't need to manually set headers
		if (!fs.existsSync(authFile)) {
			// Set header for gRPC authentication bypass/routing
			await page.setExtraHTTPHeaders({ "x-user-id": userId });

			// Set cookie for Next.js middleware and consistency
			await context.addCookies([
				{
					name: "x-user-id",
					value: userId,
					domain: domain === "localhost" ? "localhost" : domain,
					path: "/",
				},
			]);
		}

		console.log(`Verifying production environment on ${domain}`);
	});

	test("should load dashboard", async ({ page }) => {
		await page.goto("/");
		await expect(page.getByRole("main")).toBeVisible();
		// The app shell has "SwimMeet Pro" in the sidebar/header
		await expect(page.locator("body")).toContainText("SwimMeet Pro");
		// Welcome message or user content
		await expect(page.locator("body")).toContainText(/Welcome/i);
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
			page.getByRole("button", { name: /Publish to Judge App/i }),
		).toBeVisible();
	});
});
