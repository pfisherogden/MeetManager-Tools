import { defineConfig, devices } from "@playwright/test";

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
	testDir: "./tests-e2e",
	/* Run tests in files in parallel */
	fullyParallel: false,
	/* Fail the build on CI if you accidentally left test.only in the source code. */
	forbidOnly: !!process.env.CI,
	/* Retry on CI only */
	retries: process.env.CI ? 2 : 0,
	/* Opt out of parallel tests on CI. */
	workers: 1,
	/* Reporter to use. See https://playwright.dev/docs/test-reporters */
	reporter: "html",
	timeout: 300000, // 5 minutes per test
	expect: {
		timeout: 60000, // 1 minute for progress polling
	},
	/* Shared settings for all the projects below. See https://playwright.dev/api/class-testoptions. */
	use: {
		/* Base URL to use in actions like `await page.goto('/')`. */
		baseURL: process.env.FRONTEND_URL || "http://localhost:3000",

		/* Collect trace when retrying the failed test. See https://playwright.dev/trace-viewer */
		trace: "on-first-retry",
		navigationTimeout: 60000,
		actionTimeout: 120000, // 2 minutes per action
	},

	/* Configure projects for major browsers */
	projects: process.env.CI
		? [
				{
					name: "chromium",
					use: { ...devices["Desktop Chrome"] },
				},
				{
					name: "Mobile Safari",
					use: { ...devices["iPhone 12"] },
				},
			]
		: [
				{
					name: "chromium",
					use: { ...devices["Desktop Chrome"] },
				},
				/* Test against mobile viewports. */
				{
					name: "Mobile Chrome",
					use: { ...devices["Pixel 5"] },
				},
				{
					name: "Mobile Safari",
					use: { ...devices["iPhone 12"] },
				},
			],
});
