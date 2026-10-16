import { type ChildProcess, spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { test as base } from "@playwright/test";

async function getFreePort(): Promise<number> {
	return new Promise((resolve, reject) => {
		const srv = net.createServer();
		srv.listen(0, "127.0.0.1", () => {
			const addr = srv.address();
			const port = typeof addr === "object" && addr ? addr.port : 4445;
			srv.close((err) => (err ? reject(err) : resolve(port)));
		});
		srv.on("error", reject);
	});
}

async function waitForPortFree(port: number, timeoutMs = 30000): Promise<void> {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		const inUse = await new Promise<boolean>((resolve) => {
			const sock = net.connect({ port, host: "127.0.0.1" });
			sock.once("connect", () => {
				sock.destroy();
				resolve(true);
			});
			sock.once("error", () => resolve(false));
		});
		if (!inUse) return;
		await new Promise((r) => setTimeout(r, 500));
	}
	throw new Error(`CDP port ${port} is still in use after ${timeoutMs}ms`);
}

async function terminateProcess(proc: ChildProcess): Promise<void> {
	if (proc.exitCode !== null || proc.signalCode !== null) {
		proc.stdout?.destroy();
		proc.stderr?.destroy();
		return;
	}
	await new Promise<void>((resolve) => {
		let settled = false;
		const finish = () => {
			if (settled) return;
			settled = true;
			clearTimeout(killTimer);
			clearTimeout(hardTimer);
			proc.stdout?.destroy();
			proc.stderr?.destroy();
			resolve();
		};
		const killTimer = setTimeout(() => {
			try {
				proc.kill("SIGKILL");
			} catch (_e) {
				// Ignore kill errors
			}
		}, 1500);
		const hardTimer = setTimeout(() => {
			finish();
		}, 3000);
		proc.once("exit", finish);
		proc.once("close", finish);
		try {
			proc.kill();
		} catch (_e) {
			finish();
		}
	});
	killWindowsProcessTree(proc);
}

/**
 * On Windows, ChildProcess.kill() only terminates app.exe. Its WebView2 browser
 * (which owns the CDP port) and the Python backend sidecar survive, so a later test
 * can attach to the previous, dying WebView2 and fail with "socket hang up".
 * taskkill /T /F terminates the whole process tree.
 */
function killWindowsProcessTree(proc: ChildProcess): void {
	if (process.platform !== "win32" || !proc.pid) return;
	try {
		spawnSync("taskkill", ["/PID", String(proc.pid), "/T", "/F"], {
			stdio: "ignore",
			timeout: 10000,
		});
	} catch (_e) {
		// Process tree may already be gone
	}
}

export const test = base.extend<{
	tauriApp: {
		wsEndpoint: string;
		webdriverPort: number;
		saveDir: string;
		process: ChildProcess;
	};
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

		const saveDir = path.join(
			os.tmpdir(),
			`mmtools-e2e-downloads-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
		);
		fs.mkdirSync(saveDir, { recursive: true });

		const webdriverPort =
			process.platform === "darwin" ? await getFreePort() : 4445;
		// Must match --remote-debugging-port in the Windows E2E build (see desktop-build.yml).
		// WebView2 ignores WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS once Tauri sets its own browser args.
		const cdpPort = 9223;

		// Run Tauri app with remote debugging / embedded WebDriver enabled
		const env: Record<string, string | undefined> = {
			...process.env,
			TAURI_DEBUG: "1",
			TAURI_WEBVIEW_DEBUGGABLE: "1",
		};
		let tmpUserDataDir = "";
		if (process.platform === "win32") {
			// A previous test's dying WebView2 must no longer own the CDP port, otherwise we could
			// attach to it and fail with "socket hang up".
			await waitForPortFree(cdpPort);

			// Force a unique WebView2 user data folder to avoid sharing processes or file locks in parallel/sequential runs
			tmpUserDataDir = path.join(
				process.env.TEMP || process.env.TMP || "C:\\temp",
				`webview2-test-data-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
			);
			fs.mkdirSync(tmpUserDataDir, { recursive: true });
			env.WEBVIEW2_USER_DATA_FOLDER = tmpUserDataDir;
		} else if (process.platform === "darwin") {
			env.WDIO_EMBEDDED_SERVER = "true";
			env.TAURI_WEBDRIVER_PORT = String(webdriverPort);
		}

		const tauriProcess = spawn(appPath, [], {
			env: env as NodeJS.ProcessEnv,
		});

		let backendRestReady = false;
		const checkBackendReadyLog = (text: string) => {
			if (
				text.includes("Successfully connected to backend REST server") ||
				text.includes("Backend REST server failed to start")
			) {
				backendRestReady = true;
			}
		};

		// Pipe child process logs to the test console for debugging
		tauriProcess.stdout.on("data", (data) => {
			const text = data.toString().trim();
			console.log(`[Tauri App STDOUT] ${text}`);
			checkBackendReadyLog(text);
		});
		tauriProcess.stderr.on("data", (data) => {
			const text = data.toString().trim();
			console.error(`[Tauri App STDERR] ${text}`);
			checkBackendReadyLog(text);
		});

		// Wait for remote debugging websocket or WebDriver port to become active
		let wsEndpoint = "";
		if (process.platform === "win32") {
			// Poll the CDP endpoint until it is active (checking both 127.0.0.1 and localhost)
			let activeUrl = "";
			for (let i = 0; i < 120; i++) {
				for (const host of ["127.0.0.1", "localhost"]) {
					try {
						const res = await fetch(`http://${host}:${cdpPort}/json/version`);
						if (res.ok) {
							activeUrl = `http://${host}:${cdpPort}`;
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
				await terminateProcess(tauriProcess);
				throw new Error(
					`Timeout waiting for WebView2 remote debugging port ${cdpPort} to become active`,
				);
			}
			wsEndpoint = activeUrl;
		} else if (process.platform === "darwin") {
			// Wait for BOTH the Tauri .setup() backend sidecar handshake AND the embedded WebDriver server
			let activeUrl = "";
			for (let i = 0; i < 180; i++) {
				if (
					tauriProcess.exitCode !== null ||
					tauriProcess.signalCode !== null
				) {
					throw new Error(
						`Tauri process exited early with code=${tauriProcess.exitCode} signal=${tauriProcess.signalCode}`,
					);
				}
				if (backendRestReady) {
					try {
						const res = await fetch(`http://127.0.0.1:${webdriverPort}/status`);
						if (res.ok) {
							const data = (await res.json()) as {
								value?: { ready?: boolean };
							};
							if (data?.value?.ready === true) {
								activeUrl = `http://127.0.0.1:${webdriverPort}`;
								break;
							}
						}
					} catch (_e) {
						// Ignore connection errors while starting
					}
				}
				await new Promise((resolve) => setTimeout(resolve, 500));
			}
			if (!activeUrl) {
				await terminateProcess(tauriProcess);
				throw new Error(
					`Timeout waiting for macOS Tauri embedded WebDriver server on port ${webdriverPort} (backendRestReady=${backendRestReady})`,
				);
			}
			wsEndpoint = activeUrl;
		} else {
			// On Linux, parse from stderr
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

		// Pass the Tauri process and endpoints down to the test
		await use({
			wsEndpoint,
			webdriverPort,
			saveDir,
			process: tauriProcess,
		});

		// Teardown: cleanly terminate Tauri process and wait for exit so ports/locks release
		await terminateProcess(tauriProcess);

		try {
			fs.rmSync(saveDir, { recursive: true, force: true });
		} catch (_e) {
			// Ignore cleanup errors
		}

		// Clean up the temp user data directory after process exits
		if (tmpUserDataDir) {
			setTimeout(() => {
				try {
					fs.rmSync(tmpUserDataDir, { recursive: true, force: true });
				} catch (_e) {
					// Ignore lock release failures from exiting processes
				}
			}, 2000);
		}
	},
});
