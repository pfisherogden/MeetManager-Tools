import * as fs from "node:fs";
import * as path from "node:path";
import { expect, type Locator, type Page } from "@playwright/test";

export async function ensureDatasetActive(
	page: Page,
	userId: string,
	filename: string,
	data: any,
) {
	// Shard Isolation: Always use the unique userId provided by the test
	// to avoid collisions on shared runners.
	const effectiveUserId = userId;
	console.log(
		`[Utils] Ensuring ${filename} is active for ${effectiveUserId}...`,
	);

	await page.goto("/admin", { waitUntil: "networkidle" });

	// 1. Defensively check for login redirect (common in Safari)
	if (page.url().includes("/login")) {
		console.warn(
			`[Utils] Detected redirect to login on Safari. Waiting for auth redirect back...`,
		);
		await page.waitForURL("**/admin", { timeout: 20000 });
	}

	// 2. Use a robust wait for the input element
	const fileInputSelector = 'input[data-testid="dataset-file-input"]';
	try {
		await page.waitForSelector(fileInputSelector, {
			state: "attached",
			timeout: 15000,
		});
	} catch (e) {
		console.error(`[Utils] File input not found. Current URL: ${page.url()}`);
		throw e;
	}

	// 3. Check if row exists, if not upload
	const row = page.getByTestId(`dataset-row-${filename}`);
	const isPresent = (await row.count()) > 0;

	if (!isPresent) {
		console.log(`[Utils] Dataset ${filename} not found, uploading...`);
		const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
		if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
		const testFilePath = path.join(tempDir, filename);
		fs.writeFileSync(testFilePath, JSON.stringify(data));

		const fileInput = page.locator(fileInputSelector);

		// setInputFiles natively waits for the element to exist and handles hidden inputs
		console.log(`[Utils] Setting input files for ${filename}...`);
		await fileInput.setInputFiles(testFilePath, { timeout: 30000 });

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

	// Use robust click
	await robustClick(setActiveBtn);

	// NUCLEAR: Poll /meets until data is actually populated and reflected in the UI.
	// This bypasses all caching and race conditions between backend extraction and frontend revalidation.
	console.log("[Utils] Polling /meets for data readiness...");
	let isPopulated = false;
	for (let i = 0; i < 30; i++) {
		await page.goto("/meets", { waitUntil: "networkidle" });
		const tableText = await page.locator("table").textContent();
		if (tableText && !tableText.includes("No data available")) {
			isPopulated = true;
			console.log(`[Utils] Data confirmed ready on /meets after ${i + 1} retries.`);
			break;
		}
		console.log(`[Utils] Data not ready, retrying (${i + 1}/30)...`);
		await page.waitForTimeout(2000);
	}

	if (!isPopulated) {
		throw new Error(
			`[Utils] Data failed to populate for ${filename} after 60s of polling.`,
		);
	}
		);
	}

	// Go back to admin to confirm attribute change and finish utility
	await page.goto("/admin", { waitUntil: "networkidle" });
	await expect(row).toHaveAttribute("data-test-state", "active", {
		timeout: 20000,
	});
	console.log(`[Utils] ${filename} is now active and verified.`);
}

/**
 * A highly robust click helper that tries standard click first,
 * then falls back to evaluate(click) to bypass pointer-event interception
 * or layout-related visibility issues (common in React Native Web / Expo).
 */
export async function robustClick(
	locator: Locator,
	options: { timeout?: number } = {},
) {
	const timeout = options.timeout || 10000;

	try {
		// 1. Try standard click with forced visibility check
		await locator.scrollIntoViewIfNeeded();
		await locator.click({ force: true, timeout: timeout / 2 });
	} catch (e) {
		console.warn(
			`[Utils] Standard click failed, falling back to evaluate-click: ${e.message}`,
		);

		// 2. Fallback: Direct DOM click via evaluate
		// This bypasses Playwright's "is it visible/clickable" logic which
		// can be flaky with complex nested scroll views.
		await locator.evaluate((el) => {
			if (el instanceof HTMLElement) {
				el.scrollIntoView({ block: "center", inline: "center" });
				el.click();
			}
		});
	}
}

export function getFixtureData(filename: string) {
	const fixturePath = path.resolve(
		process.cwd(),
		"..",
		"tests",
		"fixtures",
		filename,
	);
	if (!fs.existsSync(fixturePath)) {
		throw new Error(`Fixture not found: ${fixturePath}`);
	}
	return JSON.parse(fs.readFileSync(fixturePath, "utf8"));
}
