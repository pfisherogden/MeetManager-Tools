import { test, expect } from '@playwright/test';

test.describe('Dashboard Smoke Test', () => {
  test('should load the dashboard with stats', async ({ page }) => {
    await page.goto('/');
    
    // Check for the sidebar (on desktop it should be visible by default)
    // Note: Aside might be hidden in DOM if it's using the Sheet component for mobile,
    // but on desktop it's a standard div/aside.
    await expect(page.getByText('SwimMeet Pro')).toBeVisible();
    
    // Check for the dashboard content
    await expect(page.getByRole('main')).toBeVisible();
    
    // Check for navigation links
    const navItems = ['Dashboard', 'Meets', 'Teams', 'Sessions', 'Events', 'Athletes', 'Entries', 'Relays', 'Scores', 'Reports', 'Admin'];
    for (const item of navItems) {
      await expect(page.getByRole('link', { name: item })).toBeVisible();
    }
  });

  test('should navigate to Meets page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Meets' }).click();
    await expect(page).toHaveURL(/\/meets/);
    await expect(page.getByRole('heading', { name: 'Meets' })).toBeVisible();
  });
});

test.describe('Mobile Responsiveness (Issue #160)', () => {
  test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE size

  test('sidebar should be hidden by default and accessible via toggle on mobile', async ({ page }) => {
    await page.goto('/');
    
    // Sidebar should be hidden initially on mobile
    await expect(page.getByText('SwimMeet Pro')).not.toBeVisible();
    
    // Toggle button should be visible
    const toggle = page.getByRole('button', { name: 'Toggle Sidebar' });
    await expect(toggle).toBeVisible();
    
    // Clicking toggle should show sidebar
    await toggle.click();
    await expect(page.getByText('SwimMeet Pro')).toBeVisible();
    
    // Clicking a link should close the sidebar (as implemented in AppSidebar)
    await page.getByRole('link', { name: 'Meets' }).click();
    await expect(page).toHaveURL(/\/meets/);
    await expect(page.getByText('SwimMeet Pro')).not.toBeVisible();
  });
});
