import { chromium, expect } from "@playwright/test";
import { test } from "./tauri.fixture";

test("Tauri Desktop App smoke test & performance check", async ({
	tauriApp,
}) => {
	// Connect Playwright to the Tauri WebView using CDP (Chrome DevTools Protocol)
	const browser = await chromium.connectOverCDP(tauriApp.wsEndpoint);
	const contexts = browser.contexts();
	const page = contexts[0].pages()[0];

	// Determine origin protocol
	const defaultUrl =
		process.platform === "win32"
			? "http://tauri.localhost/"
			: "tauri://localhost/";

	// Measure initial load time (including JVM initialization)
	const initialStart = Date.now();
	await page.goto(defaultUrl);
	await expect(page.locator("text=Dataset Management")).toBeVisible({
		timeout: 30000,
	});
	const initialDuration = Date.now() - initialStart;
	console.log(`Initial page load completed in ${initialDuration}ms`);

	// Measure consecutive load performance (verifies cache hit / no slow DB reload)
	const navStart = Date.now();
	await page.goto(defaultUrl);
	await expect(page.locator("text=Dataset Management")).toBeVisible({
		timeout: 15000,
	});
	const navDuration = Date.now() - navStart;
	console.log(`Consecutive page load completed in ${navDuration}ms`);

	// Assert that cached navigation is fast (under 1500ms)
	expect(navDuration).toBeLessThan(1500);
});
