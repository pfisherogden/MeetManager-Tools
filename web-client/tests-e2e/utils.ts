import * as fs from "node:fs";
import * as path from "node:path";
import {
	expect,
	type Locator,
	type Page,
	type TestInfo,
} from "@playwright/test";

/**
 * Generates a consistent test context including isolated userId
 */
export function getE2ETestContext(testInfo: TestInfo, _page?: Page) {
	const projectName = testInfo.project.name.replace(/\s+/g, "-");
	const shardIndex = process.env.SHARD_INDEX || "0";
	const workerIndex = testInfo.workerIndex || 0;
	const retry = testInfo.retry || 0;

	// Absolute isolation: unique UID per shard, worker and retry
	const userId = `e2e-${projectName}-${shardIndex}-${workerIndex}-${retry}`;

	// Helper to prefix local filenames to prevent collisions
	const getFilename = (base: string) =>
		`${base.split(".")[0]}_${shardIndex}_${workerIndex}_${retry}.json`;

	return { userId, getFilename, projectName, shardIndex, workerIndex, retry };
}

/**
 * Robust click handler that centers the element and uses evaluate as fallback.
 */
export async function robustClick(
	locator: Locator,
	options: { force?: boolean; timeout?: number; waitForState?: string } = {},
) {
	const page = locator.page();
	const timeout = options.timeout || 15000;

	// 1. Wait for hydration and fonts (if applicable)
	const body = page.locator("body");
	const hasHydratedAttr = await body.evaluate((el) =>
		el.hasAttribute("data-hydrated"),
	);
	if (hasHydratedAttr) {
		await page.waitForSelector("body[data-hydrated='true']", { timeout: 20000 });
	}
	await page.evaluate(() => document.fonts.ready);

	// 2. Ensure centered and visible
	await expect(locator).toBeVisible({ timeout });
	await locator.scrollIntoViewIfNeeded();

	if (options.waitForState) {
		await expect(locator).toHaveAttribute("data-state", options.waitForState, {
			timeout,
		});
	}

	try {
		await locator.click({
			timeout: 5000,
			force: options.force,
		});
	} catch (error) {
		console.warn(
			"[Utils] Standard click failed, falling back to evaluate:",
			error,
		);
		await locator.evaluate((el) => (el as HTMLElement).click());
	}
}

/**
 * Ensures the Judge App is loaded and hydrated.
 */
export async function waitForJudgeApp(page: Page) {
	console.log("[Utils] Waiting for Judge App hydration...");
	// Wait for the path to be correct (supporting /judge/index.html or rewritten /judge)
	await page.waitForFunction(() => window.location.pathname.includes("/judge"));

	// Wait for a core element to be visible
	await expect(
		page.getByPlaceholder("Your Name").or(page.getByText(/Events/i)).first(),
	).toBeVisible({ timeout: 45000 });

	// Ensure fonts are ready
	await page.evaluate(() => document.fonts.ready);
	console.log("[Utils] Judge App is ready.");
}

/**
 * Ensures a specific dataset is active for the current user.
 * Uses direct API polling for a faster, non-UI dependent source of truth.
 */
export async function ensureDatasetActive(
	page: Page,
	testInfo: TestInfo,
	filename: string,
	data: any,
) {
	const { userId } = getE2ETestContext(testInfo, page);
	console.log(`[Utils] Ensuring ${filename} is active for ${userId}...`);

	// 1. Hit the dedicated mock login endpoint
	const authResponse = await page.request.get(`/api/test/auth?uid=${userId}`);
	if (!authResponse.ok()) {
		throw new Error(
			`Failed to authenticate test user ${userId}: ${authResponse.status()}`,
		);
	}

	// 2. Upload dataset directly via API
	const uploadResponse = await page.request.post(
		"/api/test/status?action=upload_dataset",
		{
			data: {
				filename,
				data_json: JSON.stringify(data),
			},
			headers: { "x-user-id": userId },
		},
	);

	if (!uploadResponse.ok()) {
		const text = await uploadResponse.text();
		throw new Error(
			`Failed to upload dataset: ${uploadResponse.status()} - ${text}`,
		);
	}

	// 3. Set as active via API
	const activateResponse = await page.request.post(
		"/api/test/status?action=set_active",
		{
			data: { filename },
			headers: { "x-user-id": userId },
		},
	);

	if (!activateResponse.ok()) {
		const text = await activateResponse.text();
		throw new Error(
			`Failed to activate dataset: ${activateResponse.status()} - ${text}`,
		);
	}

	// 4. Poll until backend confirms it's fully processed and active
	await expect
		.poll(
			async () => {
				const res = await page.request.get("/api/test/status?action=list_datasets", {
					headers: { "x-user-id": userId },
				});
				if (!res.ok()) return false;
				const body = await res.json();
				const current = body.datasets?.find((d: any) => d.filename === filename);
				return current?.isActive === true;
			},
			{
				message: `Waiting for dataset ${filename} to become active for ${userId}`,
				timeout: 45000,
				intervals: [2000, 5000],
			},
		)
		.toBeTruthy();

	// 5. Navigate to ensure hydration settles on the intended page
	await page.goto("/admin", { waitUntil: "domcontentloaded" });
	const body = page.locator("body");
	await expect(body).toHaveAttribute("data-hydrated", "true", { timeout: 20000 });
	console.log(`[Utils] ${filename} is now active and verified for ${userId}.`);
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
