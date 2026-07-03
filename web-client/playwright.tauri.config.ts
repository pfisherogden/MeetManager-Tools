import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
	testDir: "./tests-e2e",
	testMatch: "**/tauri_smoke.spec.ts",
	fullyParallel: false,
	workers: 1,
	reporter: "html",
	timeout: 600000,
	use: {
		trace: "on",
		navigationTimeout: 600000,
		actionTimeout: 600000,
	},
	projects: [
		{
			name: "tauri",
			use: {
				...devices["Desktop Chrome"],
			},
		},
	],
});
