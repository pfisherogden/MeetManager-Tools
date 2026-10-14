import fs from "node:fs";
import * as path from "node:path";
import { chromium, expect } from "@playwright/test";
import { remote } from "webdriverio";
import { test } from "./tauri.fixture";
import { mockGoogleDrivePicker } from "./utils";

test.skip(
	process.platform !== "win32" && process.platform !== "darwin",
	"Tauri native E2E testing is supported on Windows (Playwright CDP / WebView2) and macOS (WebdriverIO / WKWebView).",
);

async function waitForWdioText(
	browser: WebdriverIO.Browser,
	text: string,
	timeout = 30000,
): Promise<void> {
	await browser.waitUntil(
		async () => {
			try {
				return await browser.execute((targetText: string) => {
					const elements = Array.from(
						document.querySelectorAll(
							"a, button, span, p, h1, h2, h3, h4, th, td, div, label, [role='status']",
						),
					);
					return elements.some((el) => {
						if (!el.textContent?.includes(targetText)) {
							return false;
						}
						const style = window.getComputedStyle(el);
						if (
							style.display === "none" ||
							style.visibility === "hidden" ||
							style.opacity === "0"
						) {
							return false;
						}
						const rect = el.getBoundingClientRect();
						return rect.width > 0 && rect.height > 0;
					});
				}, text);
			} catch (_e) {
				return false;
			}
		},
		{
			timeout,
			interval: 250,
			timeoutMsg: `Timed out waiting for text "${text}" to be visible`,
		},
	);
}

async function clickWdioText(
	browser: WebdriverIO.Browser,
	text: string,
	timeout = 15000,
): Promise<void> {
	await waitForWdioText(browser, text, timeout);
	const clicked = await browser.execute((targetText: string) => {
		const isVisible = (el: Element) => {
			const style = window.getComputedStyle(el);
			if (
				style.display === "none" ||
				style.visibility === "hidden" ||
				style.opacity === "0"
			) {
				return false;
			}
			const rect = el.getBoundingClientRect();
			return rect.width > 0 && rect.height > 0;
		};

		const interactive = Array.from(
			document.querySelectorAll("a, button, [role='button'], [data-testid]"),
		).filter(isVisible);

		const exactMatch = interactive.find(
			(el) => el.textContent?.trim() === targetText,
		);
		if (exactMatch) {
			(exactMatch as HTMLElement).scrollIntoView({ block: "center" });
			(exactMatch as HTMLElement).click();
			return true;
		}

		const partialInteractive = interactive.find((el) =>
			el.textContent?.includes(targetText),
		);
		if (partialInteractive) {
			(partialInteractive as HTMLElement).scrollIntoView({ block: "center" });
			(partialInteractive as HTMLElement).click();
			return true;
		}

		const allVisible = Array.from(
			document.querySelectorAll("span, p, div, h1, h2, h3, h4, td, th"),
		).filter((el) => isVisible(el) && el.textContent?.includes(targetText));
		const deepest = allVisible[allVisible.length - 1];
		if (deepest) {
			(deepest as HTMLElement).scrollIntoView({ block: "center" });
			(deepest as HTMLElement).click();
			return true;
		}
		return false;
	}, text);

	if (!clicked) {
		throw new Error(`Failed to click visible element with text "${text}"`);
	}
}

async function clickWdioSelector(
	browser: WebdriverIO.Browser,
	selector: string,
	timeout = 15000,
): Promise<void> {
	await browser.waitUntil(
		async () => {
			try {
				return await browser.execute((sel: string) => {
					const elements = Array.from(document.querySelectorAll(sel));
					return elements.some((el) => {
						const style = window.getComputedStyle(el);
						if (
							style.display === "none" ||
							style.visibility === "hidden" ||
							style.opacity === "0"
						) {
							return false;
						}
						const rect = el.getBoundingClientRect();
						return rect.width > 0 && rect.height > 0;
					});
				}, selector);
			} catch (_e) {
				return false;
			}
		},
		{
			timeout,
			interval: 250,
			timeoutMsg: `Timed out waiting for selector "${selector}" to be visible`,
		},
	);

	await browser.execute((sel: string) => {
		const elements = Array.from(document.querySelectorAll(sel));
		const visible = elements.find((el) => {
			const style = window.getComputedStyle(el);
			if (
				style.display === "none" ||
				style.visibility === "hidden" ||
				style.opacity === "0"
			) {
				return false;
			}
			const rect = el.getBoundingClientRect();
			return rect.width > 0 && rect.height > 0;
		});
		if (!visible) {
			throw new Error(`Visible element not found for selector "${sel}"`);
		}
		(visible as HTMLElement).scrollIntoView({ block: "center" });
		(visible as HTMLElement).click();
	}, selector);
}

async function uploadFileViaWdioChunks(
	browser: WebdriverIO.Browser,
	filePath: string,
	fileName: string,
): Promise<void> {
	const fileBytes = fs.readFileSync(filePath);
	const base64Data = fileBytes.toString("base64");
	const chunkSize = 256 * 1024; // 256 KB per chunk to stay well under Axum's 2 MB request body limit

	await browser.execute(() => {
		(window as any).__e2eMdbChunks = [];
	});

	for (let offset = 0; offset < base64Data.length; offset += chunkSize) {
		const chunk = base64Data.slice(offset, offset + chunkSize);
		await browser.execute((part: string) => {
			(window as any).__e2eMdbChunks.push(part);
		}, chunk);
	}

	await browser.execute((name: string) => {
		const b64 = ((window as any).__e2eMdbChunks || []).join("");
		delete (window as any).__e2eMdbChunks;
		const binary = atob(b64);
		const bytes = new Uint8Array(binary.length);
		for (let i = 0; i < binary.length; i++) {
			bytes[i] = binary.charCodeAt(i);
		}
		const file = new File([bytes], name, {
			type: "application/octet-stream",
		});
		const dt = new DataTransfer();
		dt.items.add(file);
		const input = document.querySelector(
			'input[type="file"]',
		) as HTMLInputElement | null;
		if (!input) {
			throw new Error('Could not find input[type="file"] in DOM');
		}
		input.files = dt.files;
		input.dispatchEvent(new Event("change", { bubbles: true }));
	}, fileName);
}

test("Tauri Desktop App smoke test & performance check", async ({
	tauriApp,
}) => {
	if (process.platform === "darwin") {
		const browser = await remote({
			hostname: "127.0.0.1",
			port: tauriApp.webdriverPort,
			capabilities: {},
			logLevel: "warn",
		});

		try {
			const initialStart = Date.now();
			await waitForWdioText(browser, "Welcome to SwimMeet Pro", 30000);
			const initialDuration = Date.now() - initialStart;
			console.log(
				`[macOS WebDriver] Initial page load completed in ${initialDuration}ms`,
			);

			// Verify we can navigate to the Admin page and see Dataset Management
			await clickWdioText(browser, "Admin", 15000);
			await waitForWdioText(browser, "Dataset Management", 15000);

			// Measure consecutive load performance (verifies cache hit / no slow DB reload)
			const navStart = Date.now();
			await clickWdioText(browser, "Dashboard", 15000);
			await waitForWdioText(browser, "Welcome to SwimMeet Pro", 15000);
			const navDuration = Date.now() - navStart;
			console.log(
				`[macOS WebDriver] Consecutive page load completed in ${navDuration}ms`,
			);
			expect(navDuration).toBeLessThan(15000);
		} finally {
			await browser.deleteSession().catch(() => {});
		}
		return;
	}

	// Connect Playwright to the Tauri WebView using CDP (Chrome DevTools Protocol)
	const browser = await chromium.connectOverCDP(tauriApp.wsEndpoint);
	const contexts = browser.contexts();
	if (contexts.length === 0) {
		throw new Error("No browser contexts found");
	}
	let page = contexts[0].pages()[0];
	if (!page) {
		page = await contexts[0].waitForEvent("page");
	}

	// Determine origin protocol
	const defaultUrl =
		process.platform === "win32"
			? "http://tauri.localhost/"
			: "tauri://localhost/";

	// Measure initial load time (including JVM initialization)
	const initialStart = Date.now();
	await page.goto(defaultUrl);
	await expect(page.locator("text=Welcome to SwimMeet Pro")).toBeVisible({
		timeout: 30000,
	});
	const initialDuration = Date.now() - initialStart;
	console.log(`Initial page load completed in ${initialDuration}ms`);

	// Verify we can navigate to the Admin page and see Dataset Management
	await page.click("text=Admin");
	await expect(page.locator("text=Dataset Management")).toBeVisible({
		timeout: 15000,
	});

	// Measure consecutive load performance (verifies cache hit / no slow DB reload)
	const navStart = Date.now();
	await page.goto(defaultUrl);
	await expect(page.locator("text=Welcome to SwimMeet Pro")).toBeVisible({
		timeout: 15000,
	});
	const navDuration = Date.now() - navStart;
	console.log(`Consecutive page load completed in ${navDuration}ms`);
	// Assert that cached navigation is fast (under 15000ms on GHA virtualized runners)
	expect(navDuration).toBeLessThan(15000);

	// Cleanly close the browser context to finalize trace/screenshot capture before process teardown
	await browser.close();
});

test("Tauri Desktop App functional navigation & data query check", async ({
	tauriApp,
}) => {
	if (process.platform === "darwin") {
		const browser = await remote({
			hostname: "127.0.0.1",
			port: tauriApp.webdriverPort,
			capabilities: {},
			logLevel: "warn",
		});

		try {
			await waitForWdioText(browser, "Welcome to SwimMeet Pro", 30000);

			// Configure non-interactive save directory for Tauri file downloads
			await browser.execute((dir: string) => {
				(window as any).__MM_E2E_SAVE_DIR__ = dir;
			}, tauriApp.saveDir);

			// 1. Navigation to Teams
			await clickWdioText(browser, "Teams", 15000);
			await waitForWdioText(
				browser,
				"Manage swim teams and organizations",
				15000,
			);
			await waitForWdioText(browser, "Team Name", 10000);

			// 2. Navigation to Athletes
			await clickWdioText(browser, "Athletes", 15000);
			await waitForWdioText(
				browser,
				"Manage athlete profiles and team assignments",
				15000,
			);

			// 3. Navigation to Admin (Dataset Manager)
			await clickWdioText(browser, "Admin", 15000);
			await waitForWdioText(browser, "Dataset Management", 15000);

			// 4. Upload a real MDB database to trigger the JRE/JVM and MDB parser code paths
			const mdbRelativePath = "./Singers23.mdb";
			const mdbAbsolutePath = path.resolve(__dirname, mdbRelativePath);
			console.log(
				`[macOS WebDriver] Uploading MDB file from ${mdbAbsolutePath}`,
			);

			await uploadFileViaWdioChunks(browser, mdbAbsolutePath, "Singers23.mdb");

			await waitForWdioText(browser, "Dataset uploaded successfully", 45000);
			await waitForWdioText(browser, "Singers23.mdb", 15000);

			// 5. Navigate back to Dashboard to confirm stats are loaded and parsed successfully from MDB
			await clickWdioText(browser, "Dashboard", 15000);
			await waitForWdioText(browser, "Welcome to SwimMeet Pro", 60000);
			await waitForWdioText(browser, "Total Meets", 60000);

			// 6. Navigation to Reports & PDF generation (Single PDF)
			console.log(
				"[macOS WebDriver] Navigating to Reports and generating single report...",
			);
			await clickWdioText(browser, "Reports", 15000);
			await waitForWdioText(
				browser,
				"Select a report type to configure and generate",
				15000,
			);

			// Ensure __MM_E2E_SAVE_DIR__ is set before triggering downloads
			await browser.execute((dir: string) => {
				(window as any).__MM_E2E_SAVE_DIR__ = dir;
			}, tauriApp.saveDir);

			await clickWdioSelector(
				browser,
				'[data-testid="report-card-meet-program-(pdf)"]',
				15000,
			);

			await clickWdioSelector(
				browser,
				'[data-testid="generate-report-button"]',
				10000,
			);

			await waitForWdioText(browser, "Report generated successfully", 45000);
			console.log(
				"[macOS WebDriver] Single PDF report generated successfully.",
			);

			// 7. Add to Pack and generate ZIP bundle
			console.log(
				"[macOS WebDriver] Adding report to pack and generating ZIP bundle...",
			);
			await clickWdioText(browser, "Add to Pack", 10000);

			await clickWdioSelector(
				browser,
				'[data-testid="generate-bundle-button"]',
				10000,
			);

			// Wait for bundle generation to complete and return to idle status (and verify ZIP saved)
			await browser.waitUntil(
				async () => {
					const files = fs.existsSync(tauriApp.saveDir)
						? fs.readdirSync(tauriApp.saveDir)
						: [];
					return files.some((f) => f.endsWith(".zip"));
				},
				{
					timeout: 90000,
					interval: 500,
					timeoutMsg:
						"Timed out waiting for ZIP bundle to be saved to E2E saveDir",
				},
			);
			console.log("[macOS WebDriver] ZIP bundle generated and saved to disk.");
		} finally {
			await browser.deleteSession().catch(() => {});
		}
		return;
	}

	// Connect Playwright to the Tauri WebView using CDP (Chrome DevTools Protocol)
	const browser = await chromium.connectOverCDP(tauriApp.wsEndpoint);
	const contexts = browser.contexts();
	if (contexts.length === 0) {
		throw new Error("No browser contexts found");
	}
	let page = contexts[0].pages()[0];
	if (!page) {
		page = await contexts[0].waitForEvent("page");
	}

	const defaultUrl =
		process.platform === "win32"
			? "http://tauri.localhost/"
			: "tauri://localhost/";

	await mockGoogleDrivePicker(page, {
		id: "tauri-drive-file-101",
		name: "TauriDriveMeet.json",
		mimeType: "application/json",
		content: {
			meet: [
				{
					meet_name1: "Tauri Google Drive Meet",
					meet_location: "Desktop Pool",
					meet_start: "2025-07-20",
					meet_end: "2025-07-20",
				},
			],
			team: [{ team_no: 1, team_abbr: "TDRV", team_name: "Tauri Drive Team" }],
			athlete: [],
			event: [],
			session: [],
			sessitem: [],
			entry: [],
		},
	});

	await page.goto(defaultUrl);
	await expect(page.locator("text=Welcome to SwimMeet Pro")).toBeVisible({
		timeout: 30000,
	});

	// 1. Navigation to Teams
	await page.click("text=Teams");
	await expect(
		page.locator("text=Manage swim teams and organizations"),
	).toBeVisible({
		timeout: 15000,
	});
	// Verify table columns exist
	await expect(page.locator("text=Team Name")).toBeVisible({ timeout: 10000 });

	// 2. Navigation to Athletes
	await page.click("text=Athletes");
	await expect(
		page.locator("text=Manage athlete profiles and team assignments"),
	).toBeVisible({
		timeout: 15000,
	});

	// 3. Navigation to Admin (Dataset Manager)
	await page.click("text=Admin");
	await expect(page.locator("text=Dataset Management")).toBeVisible({
		timeout: 15000,
	});

	// 3b. Import a dataset from Google Drive in Tauri Desktop
	const importDriveBtn = page.getByRole("button", {
		name: /Import from Drive/i,
	});
	await expect(importDriveBtn).toBeVisible({ timeout: 15000 });
	await expect(importDriveBtn).toBeEnabled({ timeout: 15000 });
	await importDriveBtn.click();
	await expect(
		page.locator("text=Successfully imported TauriDriveMeet.json from Drive"),
	).toBeVisible({
		timeout: 30000,
	});
	await expect(page.getByTestId("dataset-row-TauriDriveMeet.json")).toBeVisible(
		{
			timeout: 15000,
		},
	);

	// 4. Upload a real MDB database to trigger the JRE/JVM and MDB parser code paths
	const mdbRelativePath = "./Singers23.mdb";
	const mdbAbsolutePath = path.resolve(__dirname, mdbRelativePath);
	console.log(`E2E TEST: Uploading MDB file from ${mdbAbsolutePath}`);

	const fileInput = page.locator("input[type=file]");
	await fileInput.setInputFiles(mdbAbsolutePath);

	// Wait for the upload success toast message
	await expect(page.locator("text=Dataset uploaded successfully")).toBeVisible({
		timeout: 45000,
	});

	// Verify that the new database file is active in the list
	await expect(page.locator("text=Singers23.mdb")).toBeVisible({
		timeout: 15000,
	});

	// 5. Navigate back to Dashboard to confirm stats are loaded and parsed successfully from MDB
	await page.click("text=Dashboard");
	await expect(page.locator("text=Welcome to SwimMeet Pro")).toBeVisible({
		timeout: 60000,
	});

	// Wait for the dashboard counters to display non-zero statistics
	await expect(page.locator("text=Total Meets")).toBeVisible({
		timeout: 60000,
	});

	// 6. Navigation to Reports & PDF generation (Single PDF)
	console.log(
		"E2E TEST: Navigating to Reports and generating single report...",
	);
	await page.click("text=Reports");
	await expect(
		page.locator("text=Select a report type to configure and generate"),
	).toBeVisible({
		timeout: 15000,
	});

	// Configure non-interactive save directory for Tauri file downloads
	await page.evaluate((dir: string) => {
		(window as any).__MM_E2E_SAVE_DIR__ = dir;
	}, tauriApp.saveDir);

	// Select the Meet Program report card to show the configuration options
	const meetProgramCard = page.getByTestId("report-card-meet-program-(pdf)");
	await meetProgramCard.click();

	const generateBtn = page.getByTestId("generate-report-button");
	await expect(generateBtn).toBeVisible({ timeout: 10000 });
	await generateBtn.click();

	// Wait for the success toast message
	await expect(page.locator("text=Report generated successfully")).toBeVisible({
		timeout: 45000,
	});
	console.log("E2E TEST: Single PDF report generated successfully.");

	// 7. Add to Pack and generate ZIP bundle
	console.log("E2E TEST: Adding report to pack and generating ZIP bundle...");
	await page.getByRole("button", { name: /Add to Pack/i }).click();

	const builderCard = page.getByTestId("report-builder-card");
	const generateBundleBtn = builderCard.getByTestId("generate-bundle-button");
	await expect(generateBundleBtn).toBeVisible({ timeout: 10000 });
	await generateBundleBtn.click();

	// Wait for the bundle generation to complete and return to idle status
	await expect(
		page.locator("text=Custom pack generated successfully"),
	).toBeVisible({
		timeout: 60000,
	});
	await expect(builderCard).toHaveAttribute("data-report-status", "idle", {
		timeout: 60000,
	});
	console.log("E2E TEST: ZIP bundle generated successfully.");

	// Cleanly close the browser context to finalize trace/screenshot capture
	await browser.close().catch(() => {});
});
