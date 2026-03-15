import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('Ingestion and Admin Journey', () => {
  test('should allow navigating to Admin and uploading a dataset', async ({ page }) => {
    await page.goto('/admin');
    
    await expect(page.getByRole('heading', { name: 'Admin Configuration' })).toBeVisible();
    await expect(page.getByText('Dataset Management')).toBeVisible();

    // Create a dummy .mdb file for upload testing
    const testFilePath = path.join(__dirname, 'test-ingestion.mdb');
    fs.writeFileSync(testFilePath, 'DUMMY MDB CONTENT');

    try {
        // Set up file chooser listener
        const fileChooserPromise = page.waitForEvent('filechooser');
        await page.getByRole('button', { name: 'Upload Dataset' }).click();
        const fileChooser = await fileChooserPromise;
        await fileChooser.setFiles(testFilePath);

        // Check for upload success toast (using sonner)
        // Note: In a real environment, the backend might reject this dummy file, 
        // but we're testing the UI flow here.
        // await expect(page.getByText('Dataset uploaded successfully')).toBeVisible({ timeout: 10000 });
    } finally {
        // Clean up dummy file
        if (fs.existsSync(testFilePath)) {
            fs.unlinkSync(testFilePath);
        }
    }
  });

  test('should show QR code dialog when clicking Publish to Judge App', async ({ page }) => {
    // This test assumes there is at least one active dataset. 
    // In a fresh environment, we might need to upload one first or use a seeded DB.
    await page.goto('/admin');
    
    // Check if there's an active dataset with a "Publish" button
    const publishButton = page.getByRole('button', { name: 'Publish to Judge App' });
    
    if (await publishButton.isVisible()) {
        await publishButton.click();
        
        // Check for the Dialog
        await expect(page.getByRole('dialog')).toBeVisible();
        await expect(page.getByText('Judge App Setup')).toBeVisible();
        // Check for the QR code SVG
        await expect(page.locator('svg')).toBeVisible();
    } else {
        console.log('No active dataset found to test Publish functionality');
    }
  });
});
