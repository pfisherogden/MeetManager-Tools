import { chromium, expect } from "@playwright/test";
import { test } from "./tauri.fixture";

test("Tauri Desktop App smoke test", async ({ tauriApp }) => {
	// Connect Playwright to the Tauri WebView using CDP (Chrome DevTools Protocol)
	const browser = await chromium.connectOverCDP(tauriApp.wsEndpoint);
	const contexts = browser.contexts();
	const page = contexts[0].pages()[0];

	// Navigate to Tauri's local origin (tauri://localhost/)
	await page.goto("tauri://localhost/");

	// Assert that we are on the main page and can see critical elements
	await expect(page.locator("text=Dataset Management")).toBeVisible();
	await expect(page.getByTestId("upload-dataset-button")).toBeVisible();
});
