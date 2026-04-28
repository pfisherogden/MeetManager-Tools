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
export function getE2ETestContext(testInfo: TestInfo, page?: Page) {
	const shardIndex = process.env.SHARD_INDEX || "0";
	const workerIndex = testInfo.workerIndex;
	const retry = testInfo.retry;
	const projectName = testInfo.project.name.replace(/\s+/g, "-");

	// Setup console logging if page is provided
	if (page) {
		console.log(
			`[Utils] Attaching console listener for project: ${projectName}`,
		);
		page.on("console", (msg) => {
			console.log(
				`[Browser Console] [${projectName}] ${msg.type()}: ${msg.text()}`,
			);
		});
	}

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
	
	// Add delay and reload to ensure console logs are captured and HMR/FastRefresh settle
	console.log("[Utils] Waiting for initial page load to settle...");
	await page.waitForTimeout(5000);
	await page.reload({ waitUntil: "networkidle" });

	// Defensively check for login redirect (common in resource-constrained Safari runners)
	// But only wait if we are actually stuck on the login page.
	if (page.url().includes("/login")) {
		try {
			console.warn(`[Utils] Detected redirect to login. Attempting to wait for auth-bypass to redirect back...`);
			await page.waitForURL("**/admin", { timeout: 10000 });
		} catch (e) {
			console.error(`[Utils] Stuck on login page even with bypass. Current URL: ${page.url()}`);
			// Fallback: try going to admin again directly
			await page.goto("/admin", { waitUntil: "networkidle" });
		}
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

	// ALWAYS trigger activation to ensure backend cache is fresh and extraction is complete.
	console.log(`[Utils] Triggering activation for ${filename}...`);
	const setActiveBtn = row.getByTestId("set-active-button");
	await expect(setActiveBtn).toBeVisible({ timeout: 15000 });
	await robustClick(setActiveBtn);

	// NUCLEAR: Wait for navigation/reload after clicking Set Active
	// The UI does window.location.href = "/admin" on success.
	console.log("[Utils] Waiting for admin page reload after activation...");
	await page.waitForURL("**/admin", { timeout: 30000 });

	// NUCLEAR: Poll /meets until data is actually populated and reflected in the UI.
	console.log("[Utils] Polling /meets for data readiness...");
	let isPopulated = false;
	for (let i = 0; i < 30; i++) {
		// Reload the page each time to bypass any Next.js client-side caching
		await page.goto("/meets", { waitUntil: "networkidle" });
		await page.reload({ waitUntil: "networkidle" });

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
	options: { timeout?: number; waitForState?: string } = {},
) {
	const timeout = options.timeout || 15000;

	// 1. Wait for visibility
	await expect(locator).toBeVisible({ timeout });

	// 2. Optional: Wait for a specific data-state (useful for Radix UI / Shadcn)
	if (options.waitForState) {
		await expect(locator).toHaveAttribute("data-state", options.waitForState, {
			timeout,
		});
	}

	try {
		// 3. Attempt standard click
		await locator.click({ timeout: 5000 });
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : String(error);
		console.log(
			`[Utils] Standard click failed, falling back to evaluate-click: ${errorMessage}`,
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
