import { expect, test } from "@playwright/test";

/**
 * Production Validation Suite
 *
 * These tests are intended to run against a live production environment (e.g., Cloud Run).
 * They verify that the main application is up, authenticated, and can load data.
 *
 * IMPORTANT: These tests assume they are running against a user that already has data
 * or they will verify the 'Empty State' UI.
 */

test.describe("Production Smoke Tests", () => {
	test.beforeEach(async ({ page, context }) => {
		// Use a dedicated verification user ID
		const userId = process.env.PROD_VERIFY_USER_ID || "prod-verify-user";
		const domain = new URL(process.env.BASE_URL || "http://localhost:3000")
			.hostname;

		// Set header for gRPC authentication bypass/routing
		await page.setExtraHTTPHeaders({
			"x-user-id": userId,
		});

		// Set cookie for Next.js middleware and consistency
		await context.addCookies([
			{
				name: "x-user-id",
				value: userId,
				domain: domain === "localhost" ? "localhost" : domain,
				path: "/",
			},
		]);

		console.log(
			`Verifying production environment as User: ${userId} on ${domain}`,
		);
	});

	test("should load dashboard", async ({ page }) => {
		await page.goto("/");
		await expect(page.getByRole("main")).toBeVisible();
		// The app shell has "SwimMeet Pro" in the sidebar/header
		await expect(page.locator("body")).toContainText("SwimMeet Pro");
		// Welcome message
		await expect(page.getByText(/Welcome to SwimMeet Pro/i)).toBeVisible();
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
