import * as path from "node:path";
import { chromium, expect } from "@playwright/test";
import { test } from "./tauri.fixture";

test.skip(
	process.platform !== "win32",
	"Playwright CDP E2E testing of native WebViews is only supported on Windows (WebView2). macOS uses WebKit (WKWebView) which does not expose a CDP endpoint.",
);

test("Tauri Desktop App smoke test & performance check", async ({
	tauriApp,
}) => {
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

	// Assert the status transitions to bundling
	await expect(builderCard).toHaveAttribute("data-report-status", "bundling", {
		timeout: 15000,
	});

	// Wait for the bundle generation to complete and return to idle status
	await expect(builderCard).toHaveAttribute("data-report-status", "idle", {
		timeout: 60000,
	});
	console.log("E2E TEST: ZIP bundle generated successfully.");

	// Cleanly close the browser context to finalize trace/screenshot capture
	await browser.close();
});
