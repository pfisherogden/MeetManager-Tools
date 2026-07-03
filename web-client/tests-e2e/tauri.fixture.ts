import { spawn } from "node:child_process";
import path from "node:path";
import { test as base } from "@playwright/test";

export const test = base.extend<{
	tauriApp: { wsEndpoint: string; process: any };
}>({
	// biome-ignore lint/correctness/noEmptyPattern: Playwright requires object destructuring for first argument of fixtures
	tauriApp: async ({}, use) => {
		// Path to built macOS app executable
		const appPath = path.resolve(
			__dirname,
			"../src-tauri/target/release/bundle/macos/MM-Tools.app/Contents/MacOS/MM-Tools",
		);

		// Run Tauri app with remote debugging enabled
		const tauriProcess = spawn(appPath, [], {
			env: {
				...process.env,
				TAURI_DEBUG: "1",
			},
		});

		// Wait for remote debugging websocket to print in stdout/stderr
		let wsEndpoint = "";
		await new Promise<void>((resolve, reject) => {
			const timeout = setTimeout(() => {
				reject(
					new Error("Timeout waiting for Tauri remote debugging WebSocket"),
				);
			}, 30000);

			tauriProcess.stderr.on("data", (data) => {
				const text = data.toString();
				const match = text.match(
					/DevTools listening on (ws:\/\/localhost:\d+\/devtools\/browser\/[a-f0-9-]+)/,
				);
				if (match) {
					wsEndpoint = match[1];
					clearTimeout(timeout);
					resolve();
				}
			});

			tauriProcess.on("close", (code) => {
				clearTimeout(timeout);
				reject(new Error(`Tauri process exited early with code ${code}`));
			});
		});

		// Pass the Tauri process down to Playwright to control
		await use({ wsEndpoint, process: tauriProcess });

		// Teardown
		tauriProcess.kill();
	},
});
