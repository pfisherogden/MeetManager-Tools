import { spawn } from "node:child_process";
import fs from "node:fs";
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
				// On macOS, try the bundle first (checking both MM-Tools and app executables), fallback to the bare target binary
				const bundlePath1 = path.resolve(
					__dirname,
					`../src-tauri/target/${targetDir}/bundle/macos/MM-Tools.app/Contents/MacOS/MM-Tools`,
				);
				const bundlePath2 = path.resolve(
					__dirname,
					`../src-tauri/target/${targetDir}/bundle/macos/MM-Tools.app/Contents/MacOS/app`,
				);
				const barePath = path.resolve(
					__dirname,
					`../src-tauri/target/${targetDir}/app`,
				);
				if (fs.existsSync(bundlePath1)) {
					appPath = bundlePath1;
				} else if (fs.existsSync(bundlePath2)) {
					appPath = bundlePath2;
				} else {
					appPath = barePath;
				}
			} else {
				// On Linux, the binary is app
				appPath = path.resolve(
					__dirname,
					`../src-tauri/target/${targetDir}/app`,
				);
			}
		}

		// Ensure the binary exists before spawning
		if (!fs.existsSync(appPath)) {
			throw new Error(
				`Tauri binary not found at "${appPath}".\n` +
					`Please compile the desktop app first by running:\n` +
					`  cd web-client && npx tauri build`,
			);
		}

		// Run Tauri app with remote debugging enabled
		const env: Record<string, string> = {
			...process.env,
			TAURI_DEBUG: "1",
			TAURI_WEBVIEW_DEBUGGABLE: "1",
		};
		if (process.platform === "win32") {
			// On Windows, WebView2 requires WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS to expose remote debugging CDP
			env.WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS =
				"--remote-debugging-port=9222";
		}

		const tauriProcess = spawn(appPath, [], { env });

		// Pipe child process logs to the test console for debugging
		tauriProcess.stdout.on("data", (data) => {
			console.log(`[Tauri App STDOUT] ${data.toString().trim()}`);
		});
		tauriProcess.stderr.on("data", (data) => {
			console.error(`[Tauri App STDERR] ${data.toString().trim()}`);
		});

		// Wait for remote debugging websocket or port to become active
		let wsEndpoint = "";
		if (process.platform === "win32") {
			// Poll the CDP endpoint until it is active (checking both 127.0.0.1 and localhost)
			let activeUrl = "";
			for (let i = 0; i < 120; i++) {
				for (const host of ["127.0.0.1", "localhost"]) {
					try {
						const res = await fetch(`http://${host}:9222/json/version`);
						if (res.ok) {
							activeUrl = `http://${host}:9222`;
							break;
						}
					} catch (_e) {
						// Ignore connection errors
					}
				}
				if (activeUrl) {
					break;
				}
				await new Promise((resolve) => setTimeout(resolve, 500));
			}
			if (!activeUrl) {
				throw new Error(
					"Timeout waiting for WebView2 remote debugging port 9222 to become active",
				);
			}
			wsEndpoint = activeUrl;
		} else {
			// On macOS/Linux, parse from stderr
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
		}

		// Pass the Tauri process down to Playwright to control
		await use({ wsEndpoint, process: tauriProcess });

		// Teardown
		tauriProcess.kill();
	},
});
