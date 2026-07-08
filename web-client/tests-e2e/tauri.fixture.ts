import { spawn } from "node:child_process";
import path from "node:path";
import { test as base } from "@playwright/test";

export const test = base.extend<{
	tauriApp: { wsEndpoint: string; process: any };
}>({
	// biome-ignore lint/correctness/noEmptyPattern: Playwright requires object destructuring for first argument of fixtures
	tauriApp: async ({}, use) => {
		// Determine the binary path
		let appPath = process.env.TAURI_APP_PATH;
		if (!appPath) {
			const targetDir =
				process.env.TAURI_BUILD_PROFILE === "debug" ? "debug" : "release";
			if (process.platform === "win32") {
				// On Windows, the binary is app.exe
				appPath = path.resolve(
					__dirname,
					`../src-tauri/target/${targetDir}/app.exe`,
				);
			} else if (process.platform === "darwin") {
				// On macOS, try the bundle first, fallback to the bare target binary
				const bundlePath = path.resolve(
					__dirname,
					`../src-tauri/target/${targetDir}/bundle/macos/MM-Tools.app/Contents/MacOS/app`,
				);
				const barePath = path.resolve(
					__dirname,
					`../src-tauri/target/${targetDir}/app`,
				);
				const fs = require("node:fs");
				appPath = fs.existsSync(bundlePath) ? bundlePath : barePath;
			} else {
				// On Linux, the binary is app
				appPath = path.resolve(
					__dirname,
					`../src-tauri/target/${targetDir}/app`,
				);
			}
		}

		// Run Tauri app with remote debugging enabled
		const env: Record<string, string> = {
			...process.env,
			TAURI_DEBUG: "1",
		};
		if (process.platform === "win32") {
			// On Windows, WebView2 requires WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS to expose remote debugging CDP
			env.WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = "--remote-debugging-port=0";
		}

		const tauriProcess = spawn(appPath, [], { env });

		// Wait for remote debugging websocket to print in stdout/stderr
		let wsEndpoint = "";
		await new Promise<void>((resolve, reject) => {
			const timeout = setTimeout(() => {
				reject(
					new Error(
						`Timeout waiting for Tauri remote debugging WebSocket at path: ${appPath}`,
					),
				);
			}, 30000);

			tauriProcess.stderr.on("data", (data) => {
				const text = data.toString();
				const match = text.match(
					/DevTools listening on (ws:\/\/(?:localhost|127\.0\.0\.1):\d+\/devtools\/browser\/[a-f0-9-]+)/,
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
