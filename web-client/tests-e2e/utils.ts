import * as fs from "node:fs";
import * as path from "node:path";
import {
	type APIResponse,
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
	const customToken = process.env.FIREBASE_CUSTOM_TOKEN;
	const restPort = getDynamicGatewayPort();
	const baseUrl =
		process.env.FRONTEND_URL ||
		process.env.PLAYWRIGHT_TEST_BASE_URL ||
		"http://localhost:3000";

	page.on("console", (msg) => {
		console.log(`[Browser Console] [${msg.type()}] ${msg.text()}`);
	});

	page.on("requestfailed", (request) => {
		console.log(
			`[Browser Network Error] ${request.method()} ${request.url()} failed with: ${request.failure()?.errorText}`,
		);
	});

	if (customToken) {
		try {
			await page.context().addCookies([
				{
					name: "googleAccessToken",
					value: "e2e-mock-google-oauth-token",
					url: baseUrl,
				},
			]);
		} catch (err) {
			console.warn("[Utils] Could not pre-set context cookies:", err);
		}

		await page.addInitScript(
			({ port, token }) => {
				(window as any).__MM_TEST_PORT__ = port;
				(window as any).__MM_FIREBASE_CUSTOM_TOKEN__ = token;
				(window as any).__MM_TEST_GOOGLE_TOKEN__ =
					"e2e-mock-google-oauth-token";
			},
			{ port: restPort, token: customToken },
		);

		await page.goto("/login");
		await page.waitForFunction(
			() =>
				document.cookie
					.split(";")
					.some(
						(c) =>
							c.trim().startsWith("idToken=") &&
							!c.trim().endsWith("dev-token"),
					),
			{ timeout: 30000 },
		);
		await page.evaluate(() => {
			document.cookie =
				"googleAccessToken=e2e-mock-google-oauth-token; path=/; max-age=31536000";
		});
		return { userId };
	}

	if (!isStatic) {
		// 1. Hit the dedicated mock login endpoint to synthesize session cookies on the server
		const authResponse = await page.request.post(
			`/api/test/auth?uid=${userId}`,
		);
		if (!authResponse.ok() && authResponse.status() !== 404) {
			throw new Error(
				`Failed to authenticate test user ${userId}: ${authResponse.status()}`,
			);
		}
	}

	try {
		await page.context().addCookies([
			{
				name: "x-user-id",
				value: userId,
				url: baseUrl,
			},
			{
				name: "idToken",
				value: "dev-token",
				url: baseUrl,
			},
			{
				name: "googleAccessToken",
				value: "e2e-mock-google-oauth-token",
				url: baseUrl,
			},
		]);
	} catch (err) {
		console.warn("[Utils] Could not pre-set context cookies:", err);
	}

	await page.addInitScript(
		({ port, uid }) => {
			(window as any).__MM_TEST_PORT__ = port;
			(window as any).__MM_E2E_TEST_BYPASS__ = true;
			(window as any).__MM_TEST_GOOGLE_TOKEN__ = "e2e-mock-google-oauth-token";
			try {
				window.localStorage.setItem("x-user-id", uid);
			} catch (_e) {}
		},
		{ port: restPort, uid: userId },
	);

	// Navigate to home page first so we have a valid domain context in the browser
	await page.goto("/");

	// Set cookies via document.cookie directly in the browser
	await page.evaluate((uid) => {
		document.cookie = `x-user-id=${uid}; path=/; max-age=31536000`;
		document.cookie = `idToken=dev-token; path=/; max-age=31536000`;
		document.cookie = `googleAccessToken=e2e-mock-google-oauth-token; path=/; max-age=31536000`;
	}, userId);
	console.log(
		"[Utils] Cookie immediately after set:",
		await page.evaluate(() => document.cookie),
	);

	return { userId };
}

export function getDynamicGatewayPort(): number {
	if (process.env.REST_PORT) {
		return parseInt(process.env.REST_PORT, 10);
	}
	if (process.env.BACKEND_PORT) {
		return parseInt(process.env.BACKEND_PORT, 10);
	}
	try {
		const homedir = require("node:os").homedir();
		const registryPath = path.join(homedir, ".mmtools", "active_ports.json");
		if (fs.existsSync(registryPath)) {
			const data = JSON.parse(fs.readFileSync(registryPath, "utf8"));
			if (data.rest_port) {
				console.log(
					`[E2E Utils] Discovered active REST port: ${data.rest_port}`,
				);
				return data.rest_port;
			}
		}
	} catch (e) {
		console.warn("[E2E Utils] Failed to read active ports registry:", e);
	}
	return 8081;
}

export function getDynamicGatewayUrl(): string {
	return `http://127.0.0.1:${getDynamicGatewayPort()}/api/grpc`;
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
	const gatewayUrl = getDynamicGatewayUrl();

	// 2. Upload dataset directly via API
	let uploadResponse: APIResponse;
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
	let activateResponse: APIResponse;
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

export interface MockDriveFileOptions {
	id: string;
	name: string;
	mimeType?: string;
	content: Buffer | string | Record<string, unknown>;
}

/**
 * Mocks the Google Picker UI and Google Drive v3 file download endpoint in Playwright
 * so E2E tests can verify choosing, uploading, activating, and viewing Google Drive files
 * across Local Web, Tauri Desktop, and Cloud Run deployments.
 */
export async function mockGoogleDrivePicker(
	page: Page,
	options: MockDriveFileOptions,
) {
	const payloadBuffer = Buffer.isBuffer(options.content)
		? options.content
		: Buffer.from(
				typeof options.content === "string"
					? options.content
					: JSON.stringify(options.content),
			);
	const mimeType = options.mimeType || "application/octet-stream";
	const driveDownloadRequests: { url: string; authHeader: string | null }[] =
		[];

	// 1. Stub external GAPI / GSI scripts so they never overwrite our mock or fail offline
	await page.route("https://apis.google.com/**", async (route) => {
		await route.fulfill({
			status: 200,
			contentType: "application/javascript",
			body: "window.gapi = window.gapi || { load: function(_n, cb) { if (cb) cb(); } };",
		});
	});
	await page.route("https://accounts.google.com/gsi/client", async (route) => {
		await route.fulfill({
			status: 200,
			contentType: "application/javascript",
			body: "/* mocked gsi client */",
		});
	});

	// 2. Intercept Google Drive API v3 media download requests
	await page.route(
		"https://www.googleapis.com/drive/v3/files/**",
		async (route) => {
			const req = route.request();
			if (req.method() !== "OPTIONS") {
				driveDownloadRequests.push({
					url: req.url(),
					authHeader: req.headers().authorization || null,
				});
			}
			await route.fulfill({
				status: 200,
				contentType: mimeType,
				headers: {
					"Access-Control-Allow-Origin": "*",
					"Access-Control-Allow-Methods": "GET, POST, OPTIONS",
					"Access-Control-Allow-Headers": "Authorization, Content-Type",
				},
				body: payloadBuffer,
			});
		},
	);

	const pickerDoc = {
		id: options.id,
		name: options.name,
		mimeType,
		sizeBytes: payloadBuffer.length,
		payloadBase64: payloadBuffer.toString("base64"),
	};

	const installPickerMock = (doc: typeof pickerDoc) => {
		(window as any).__MM_MOCK_DRIVE_DOC__ = doc;
		(window as any).__MM_TEST_GOOGLE_TOKEN__ =
			(window as any).__MM_TEST_GOOGLE_TOKEN__ || "e2e-mock-google-oauth-token";
		try {
			document.cookie =
				"googleAccessToken=e2e-mock-google-oauth-token; path=/; max-age=31536000";
		} catch (_e) {}

		if (!(window as any).__MM_DRIVE_FETCH_WRAPPED__ && window.fetch) {
			(window as any).__MM_DRIVE_FETCH_WRAPPED__ = true;
			const origFetch = window.fetch.bind(window);
			window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
				const url =
					typeof input === "string"
						? input
						: input instanceof URL
							? input.toString()
							: input.url;
				if (url.includes("googleapis.com/drive/v3/files/")) {
					try {
						const res = await origFetch(input, init);
						if (res.ok) return res;
					} catch (_err) {
						// Fall back to in-page mock response when CDP/CORS blocks external request
					}
					const activeDoc = (window as any).__MM_MOCK_DRIVE_DOC__ || doc;
					const binary = window.atob(activeDoc.payloadBase64 || "");
					const bytes = new Uint8Array(binary.length);
					for (let i = 0; i < binary.length; i++) {
						bytes[i] = binary.charCodeAt(i);
					}
					return new Response(bytes, {
						status: 200,
						headers: { "Content-Type": activeDoc.mimeType },
					});
				}
				return origFetch(input, init);
			};
		}

		(window as any).gapi = {
			load: (_name: string, cb?: () => void) => {
				if (cb) cb();
			},
		};

		(window as any).google = {
			picker: {
				ViewId: { DOCS: "all" },
				Action: { PICKED: "picked", CANCEL: "cancel" },
				DocsView: function (this: any) {
					this.setIncludeFolders = () => this;
					this.setSelectFolderEnabled = () => this;
					return this;
				},
				PickerBuilder: function (this: any) {
					let callback: ((data: any) => void) | null = null;
					this.addView = () => this;
					this.setOAuthToken = () => this;
					this.setDeveloperKey = () => this;
					this.setAppId = () => this;
					this.setOrigin = () => this;
					this.setCallback = (cb: (data: any) => void) => {
						callback = cb;
						return this;
					};
					this.build = () => ({
						setVisible: (visible: boolean) => {
							if (visible && callback) {
								(window as any).__MM_PICKER_OPENED__ = true;
								setTimeout(() => {
									const activeDoc =
										(window as any).__MM_MOCK_DRIVE_DOC__ || doc;
									callback?.({
										action: "picked",
										docs: [activeDoc],
									});
								}, 10);
							}
						},
					});
					return this;
				},
			},
		};

		const existingScript = document.querySelector<HTMLScriptElement>(
			'script[src="https://apis.google.com/js/api.js"]',
		);
		if (existingScript) {
			existingScript.dispatchEvent(new Event("load"));
		}
	};

	await page.addInitScript(installPickerMock, pickerDoc);
	try {
		await page.evaluate(installPickerMock, pickerDoc);
	} catch (_e) {
		// Page may not have navigated yet; addInitScript will run on navigation
	}

	return { driveDownloadRequests };
}
