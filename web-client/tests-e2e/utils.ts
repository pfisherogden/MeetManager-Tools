import * as fs from "node:fs";
import * as path from "node:path";
import {
	expect,
	type Locator,
	type Page,
	type TestInfo,
} from "@playwright/test";

/**
 * Generates a consistent test context including isolated UID and filenames.
 * This ensures that shard, worker, and retry indices are identical across all hooks and test cases.
 */
export function getE2ETestContext(testInfo: TestInfo) {
	const shardIndex = process.env.SHARD_INDEX || "0";
	const workerIndex = testInfo.workerIndex;
	const retry = testInfo.retry;
	const projectName = testInfo.project.name.replace(/\s+/g, "-");

	// Isolated User ID for the entire shard+worker+retry combination
	const userId =
		process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true"
			? `e2e-bypass-${shardIndex}-${workerIndex}-${retry}`
			: `e2e-user-${shardIndex}-${workerIndex}-${retry}-${projectName}`;

	return {
		userId,
		shardIndex,
		workerIndex,
		retry,
		projectName,
		// Generate unique filenames to prevent shard collision on shared filesystems
		getFilename: (base: string) =>
			`${base.split(".")[0]}_${shardIndex}_${workerIndex}_${retry}.json`,
	};
}

export async function ensureDatasetActive(
	page: Page,
	userId: string,
	filename: string,
	data: any,
) {
	console.log(`[Utils] Ensuring ${filename} is active for ${userId}...`);

	await page.goto("/admin", { waitUntil: "networkidle" });

	// Defensively check for login redirect (common in Safari)
	if (page.url().includes("/login")) {
		console.warn(
			`[Utils] Detected redirect to login on Safari. Waiting for auth redirect back...`,
		);
		await page.waitForURL("**/admin", { timeout: 20000 });
	}

	// Use a robust wait for the input element
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

	const row = page.getByTestId(`dataset-row-${filename}`);
	const isPresent = (await row.count()) > 0;

	if (!isPresent) {
		console.log(`[Utils] Dataset ${filename} not found, uploading...`);
		const tempDir = path.join(process.cwd(), "tmp", "e2e-fixtures");
		if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
		const testFilePath = path.join(tempDir, filename);
		fs.writeFileSync(testFilePath, JSON.stringify(data));

		const fileInput = page.locator(fileInputSelector);
		console.log(`[Utils] Setting input files for ${filename}...`);
		await fileInput.setInputFiles(testFilePath, { timeout: 30000 });

		// Wait for row to appear
		await expect(row).toBeVisible({ timeout: 60000 });
		console.log(`[Utils] ${filename} uploaded successfully.`);
	}

	// Check if already active
	const state = await row.getAttribute("data-test-state");
	if (state !== "active") {
		console.log(`[Utils] Setting ${filename} active...`);
		const setActiveBtn = row.getByTestId("set-active-button");
		await expect(setActiveBtn).toBeVisible({ timeout: 15000 });
		await robustClick(setActiveBtn);
	} else {
		console.log(`[Utils] ${filename} is already active.`);
	}

	// NUCLEAR: Poll /meets until data is actually populated and reflected in the UI.
	console.log("[Utils] Polling /meets for data readiness...");
	let isPopulated = false;
	for (let i = 0; i < 30; i++) {
		await page.goto("/meets", { waitUntil: "networkidle" });
		const tableText = await page.locator("table").textContent();
		if (tableText && !tableText.includes("No data available")) {
			isPopulated = true;
			console.log(
				`[Utils] Data confirmed ready on /meets after ${i + 1} retries.`,
			);
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

	// Go back to admin to confirm final state
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
		// Attempt standard click
		await locator.click({ timeout });
	} catch (error) {
		console.log(
			`[Utils] Standard click failed, falling back to evaluate-click: ${error.message}`,
		);
		// Fallback to JS click which bypasses pointer-events: none and occlusion
		await locator.evaluate((el) => (el as HTMLElement).click());
	}
}

export function getFixtureData(filename: string) {
	const fixturePath = path.join(
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
