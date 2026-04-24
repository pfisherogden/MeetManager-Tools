import * as fs from "node:fs";
import * as path from "node:path";
import { expect, type Page } from "@playwright/test";

export async function ensureDatasetActive(
	page: Page,
	userId: string,
	filename: string,
	data: any,
) {
	console.log(`[Utils] Ensuring ${filename} is active for ${userId}...`);

	await page.goto("/admin", { waitUntil: "networkidle" });

	// 1. Check if row exists, if not upload
	const row = page.getByTestId(`dataset-row-${filename}`);
	const isPresent = (await row.count()) > 0;

	if (!isPresent) {
		console.log(`[Utils] Dataset ${filename} not found, uploading...`);
		const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
		if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
		const testFilePath = path.join(tempDir, filename);
		fs.writeFileSync(testFilePath, JSON.stringify(data));

		await page.setInputFiles('input[type="file"]', testFilePath);
		await page.getByText(/Upload Dataset/i).click();

		// Wait for row without checking toast
		await expect(row).toBeVisible({ timeout: 60000 });
		console.log(`[Utils] ${filename} uploaded successfully.`);
	}

	// 2. Check if active via data-attribute
	const state = await row.getAttribute("data-test-state");
	if (state === "active") {
		console.log(`[Utils] ${filename} is already active.`);
		return;
	}

	// 3. Set active
	console.log(`[Utils] Setting ${filename} active...`);
	await row.scrollIntoViewIfNeeded();
	const setActiveBtn = row.getByTestId("set-active-button");
	await expect(setActiveBtn).toBeVisible({ timeout: 15000 });

	await setActiveBtn.click();

	// Wait for attribute change - MUCH more robust than toast
	await expect(row).toHaveAttribute("data-test-state", "active", {
		timeout: 30000,
	});
	console.log(`[Utils] ${filename} is now active.`);
}

export function getFixtureData(filename: string) {
	return JSON.parse(
		fs.readFileSync(
			path.resolve(process.cwd(), "..", "tests", "fixtures", filename),
			"utf8",
		),
	);
}
