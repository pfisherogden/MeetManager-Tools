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
		await page.waitForSelector("body[data-hydrated='true']", {
			timeout: 20000,
		});
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
		page
			.getByPlaceholder("Your Name")
			.or(page.getByText(/Events/i))
			.first(),
	).toBeVisible({ timeout: 45000 });

	// Ensure fonts are ready
	await page.evaluate(() => document.fonts.ready);
	console.log("[Utils] Judge App is ready.");
}

/**
 * Sets up a valid E2E session by injecting cookies and hitting the mock auth endpoint.
 */
export async function setupE2ESession(page: Page, testInfo: TestInfo) {
	const { userId } = getE2ETestContext(testInfo, page);

	const isStatic = process.env.TEST_STATIC === "true";

	if (!isStatic) {
		// 1. Hit the dedicated mock login endpoint to synthesize session cookies on the server
		const authResponse = await page.request.post(
			`/api/test/auth?uid=${userId}`,
		);
		if (!authResponse.ok()) {
			throw new Error(
				`Failed to authenticate test user ${userId}: ${authResponse.status()}`,
			);
		}
	}

	// Navigate to home page first so we have a valid domain context in the browser
	await page.goto("/");

	// Set cookies via document.cookie directly in the browser
	await page.evaluate((uid) => {
		document.cookie = `x-user-id=${uid}; path=/; max-age=31536000`;
		document.cookie = `idToken=dev-token; path=/; max-age=31536000`;
	}, userId);
	console.log("[Utils] Cookie immediately after set:", await page.evaluate(() => document.cookie));

	page.on("console", (msg) => {
		console.log(`[Browser Console] [${msg.type()}] ${msg.text()}`);
	});

	return { userId };
}

/**
 * Ensures a specific dataset is active for the current user.
 */
export async function ensureDatasetActive(
	page: Page,
	testInfo: TestInfo,
	filename: string,
	data: any,
) {
	const { userId } = await setupE2ESession(page, testInfo);
	console.log(`[Utils] Ensuring ${filename} is active for ${userId}...`);

	const isStatic = process.env.TEST_STATIC === "true";
	const gatewayUrl = "http://localhost:8081/api/grpc";

	// 2. Upload dataset directly via API
	let uploadResponse;
	if (isStatic) {
		const base64Content = Buffer.from(JSON.stringify(data)).toString("base64");
		uploadResponse = await page.request.post(`${gatewayUrl}/UploadDataset`, {
			data: {
				filename,
				content: base64Content,
			},
			headers: { "x-user-id": userId },
		});
	} else {
		uploadResponse = await page.request.post(
			"/api/test/status?action=upload_dataset",
			{
				data: {
					filename,
					data_json: JSON.stringify(data),
				},
				headers: { "x-user-id": userId },
			},
		);
	}

	if (!uploadResponse.ok()) {
		const text = await uploadResponse.text();
		throw new Error(
			`Failed to upload dataset: ${uploadResponse.status()} - ${text}`,
		);
	}

	// 3. Set as active via API
	let activateResponse;
	if (isStatic) {
		activateResponse = await page.request.post(
			`${gatewayUrl}/SetActiveDataset`,
			{
				data: { filename },
				headers: { "x-user-id": userId },
			},
		);
	} else {
		activateResponse = await page.request.post(
			"/api/test/status?action=set_active",
			{
				data: { filename },
				headers: { "x-user-id": userId },
			},
		);
	}

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
				const res = isStatic
					? await page.request.post(`${gatewayUrl}/ListDatasets`, {
							data: {},
							headers: { "x-user-id": userId },
						})
					: await page.request.get("/api/test/status?action=list_datasets", {
							headers: { "x-user-id": userId },
						});
				if (!res.ok()) return false;
				const body = await res.json();
				const current = body.datasets?.find(
					(d: any) => d.filename === filename,
				);
				return current?.isActive === true || current?.is_active === true;
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
	await page.waitForSelector("body[data-hydrated='true']");
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
