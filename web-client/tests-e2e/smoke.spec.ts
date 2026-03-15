import { expect, test } from "@playwright/test";

test.describe("Dashboard Smoke Test", () => {
	test("should load the dashboard with stats", async ({ page }) => {
		await page.goto("/");

		// Check for the dashboard content
		await expect(page.getByRole("main")).toBeVisible();

		// Check for navigation links in the sidebar (only if viewport is desktop)
		const isMobile = page.viewportSize()!.width < 768;
		if (!isMobile) {
			// Check for the sidebar header text
			await expect(
				page.locator('[data-slot="sidebar-header"]').getByText("SwimMeet Pro"),
			).toBeVisible();

			const navItems = [
				"Dashboard",
				"Meets",
				"Teams",
				"Sessions",
				"Events",
				"Athletes",
				"Entries",
				"Relays",
				"Scores",
				"Reports",
				"Admin",
			];
			const sidebar = page.locator('[data-slot="sidebar"]');
			for (const item of navItems) {
				await expect(
					sidebar.getByRole("link", { name: item, exact: true }),
				).toBeVisible();
			}
		} else {
			// On mobile, check that the mobile header is visible
			await expect(
				page.getByRole("button", { name: "Toggle Sidebar" }),
			).toBeVisible();
		}
	});

	test("should navigate to Meets page", async ({ page }) => {
		await page.goto("/");
		const isMobile = page.viewportSize()!.width < 768;

		if (isMobile) {
			// On mobile, need to open the sidebar first
			await page.getByRole("button", { name: "Toggle Sidebar" }).click();
			// Wait for sidebar to be visible
			await expect(page.locator('[data-sidebar="sidebar"]')).toBeVisible();
		}

		// Click the Meets link in the sidebar
		await page
			.locator('[data-sidebar="sidebar"]')
			.getByRole("link", { name: "Meets", exact: true })
			.click();
		await expect(page).toHaveURL(/\/meets/);
		await expect(
			page.getByRole("heading", { name: "Meets", exact: true }),
		).toBeVisible();
	});
});

test.describe("Mobile Responsiveness (Issue #160)", () => {
	test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE size

	test("sidebar should be hidden by default and accessible via toggle on mobile", async ({
		page,
	}) => {
		await page.goto("/");

		// Sidebar should be hidden initially on mobile
		// We check that the sidebar container itself is not visible or has data-state="closed"
		const sidebar = page.locator('[data-sidebar="sidebar"]');
		await expect(sidebar).not.toBeVisible();

		// Toggle button should be visible in the mobile header
		const toggle = page.getByRole("button", { name: "Toggle Sidebar" });
		await expect(toggle).toBeVisible();

		// Clicking toggle should show sidebar (Sheet)
		await toggle.click();
		await expect(sidebar).toBeVisible();
		await expect(sidebar.getByText("SwimMeet Pro")).toBeVisible();

		// Clicking a link should close the sidebar
		await sidebar.getByRole("link", { name: "Meets", exact: true }).click();
		await expect(page).toHaveURL(/\/meets/);

		// On mobile, the sidebar should close after navigation
		await expect(sidebar).not.toBeVisible();
	});
});
