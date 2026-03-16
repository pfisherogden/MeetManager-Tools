import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('Bug Reproduction - Issue #174', () => {
  test('reproduce bugs with Champs dataset', async ({ page }) => {
    // Increase timeout for this test
    test.setTimeout(120000);

    // 1. Upload and Set Active
    await page.goto('http://localhost:3000/admin');
    
    const testFileName = 'sample_data_champs_2025-aftermeet.mdb';
    const testFilePath = path.resolve(__dirname, '../../backend/data/' + testFileName);
    
    // Check if already uploaded
    const existingRow = page.locator('tr').filter({ hasText: testFileName });
    if (await existingRow.count() === 0) {
        const fileChooserPromise = page.waitForEvent('filechooser');
        await page.getByRole('button', { name: 'Upload Dataset' }).click();
        const fileChooser = await fileChooserPromise;
        await fileChooser.setFiles(testFilePath);
        await expect(page.getByText('Dataset uploaded successfully')).toBeVisible({ timeout: 20000 });
    }
    
    // Set as active
    const datasetRow = page.locator('tr').filter({ hasText: testFileName });
    const activeBadge = datasetRow.locator('.bg-green-100');
    if (await activeBadge.count() === 0) {
        await datasetRow.getByRole('button', { name: 'Set Active' }).click();
        await expect(page.getByText('Active dataset changed')).toBeVisible();
    }

    // BUG 1: Check if config.json can be set active
    const configRow = page.locator('tr').filter({ hasText: 'config.json' });
    if (await configRow.count() > 0) {
        console.log('BUG 1 REPRODUCED: config.json is visible in dataset list');
    }

    // BUG 2: Meets Page - "unknown meet"
    await page.goto('http://localhost:3000/meets');
    await page.waitForTimeout(5000); // Wait for data to load
    const meetTable = page.locator('table');
    const meetText = await meetTable.innerText();
    if (meetText.toLowerCase().includes('unknown')) {
        console.log('BUG 2 REPRODUCED: "unknown meet" found in meets table');
    } else {
        console.log('Meet data found:', meetText.substring(0, 100));
    }

    // BUG 3: Teams Page
    await page.goto('http://localhost:3000/teams');
    await page.waitForTimeout(2000);
    const teamsTable = page.locator('table');
    if (await page.getByText('no data available', { exact: false }).isVisible()) {
        console.log('BUG 3 REPRODUCED: No data available on Teams page');
    }

    // BUG 4: Athletes Page
    await page.goto('http://localhost:3000/athletes');
    await page.waitForTimeout(2000);
    if (await page.getByText('no data available', { exact: false }).isVisible()) {
        console.log('BUG 4 REPRODUCED: No data available on Athletes page');
    }

    // BUG 5: Decimal places
    await page.goto('http://localhost:3000/entries');
    await page.waitForTimeout(2000);
    const bodyText = await page.innerText('body');
    const longDecimals = bodyText.match(/\d+\.\d{4,}/);
    if (longDecimals) {
        console.log('BUG 5 REPRODUCED: Found long decimal:', longDecimals[0]);
    }

    // BUG 7: Reports Bundle
    await page.goto('http://localhost:3000/reports');
    const generateBundle = page.getByRole('button', { name: /Generate/i }).first();
    await generateBundle.click();
    // Check for error toast
    const errorToast = page.getByText('bundle generation failed', { exact: false });
    try {
        await expect(errorToast).toBeVisible({ timeout: 10000 });
        console.log('BUG 7 REPRODUCED: Bundle generation failed');
    } catch (e) {
        console.log('BUG 7 NOT REPRODUCED in 10s');
    }
  });
});
