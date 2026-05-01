import { expect, test } from "@playwright/test";

test.describe("Security and Access Control", () => {
	test("should redirect unauthenticated users from dashboard to login", async ({
		page,
	}) => {
		// Ensure no cookies are set
		await page.context().clearCookies();

		// Attempt to access dashboard
		await page.goto("/");

		// Verify redirect to login
		await expect(page).toHaveURL(/\/login/);
		await expect(
			page.getByText(/Sign in with your Google account/i).first(),
		).toBeVisible();
	});

	test("should redirect unauthenticated users from admin to login", async ({
		page,
	}) => {
		await page.context().clearCookies();
		await page.goto("/admin");
		await expect(page).toHaveURL(/\/login/);
	});

	test("should allow unauthenticated access to judge app", async ({ page }) => {
		await page.context().clearCookies();
		// We use a dummy URL that matches the /judge path
		await page.goto("/judge/index.html");
		// It should NOT redirect to login (it might show an error if data is missing, but not a login redirect)
		await expect(page).not.toHaveURL(/\/login/);
	});

	test("should block /api/data without a valid token", async ({ page }) => {
		await page.context().clearCookies();
		const response = await page.request.get(
			"/api/data?path=users/private/data.json",
		);
		expect(response.status()).toBe(403);
	});

	test("should allow /api/data for sample paths without a token", async ({
		page,
	}) => {
		await page.context().clearCookies();
		const response = await page.request.get(
			"/api/data?path=users/sample-user/tiny_meet.json",
		);
		// Status might be 404 if file doesn't exist, but not 403
		expect(response.status()).not.toBe(403);
	});
});
