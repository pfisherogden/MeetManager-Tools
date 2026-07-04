import { invoke } from "@tauri-apps/api/core";

let cachedRestPort: number | null = null;

export async function getRestPort(): Promise<number> {
	if (cachedRestPort !== null) return cachedRestPort;

	// In E2E tests, read from window.__MM_TEST_PORT__ if set
	if (typeof window !== "undefined" && (window as any).__MM_TEST_PORT__) {
		cachedRestPort = (window as any).__MM_TEST_PORT__;
		return cachedRestPort!;
	}

	try {
		if (typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__) {
			const portStr = await invoke<string>("get_backend_port");
			const restPort = Number.parseInt(portStr, 10);
			cachedRestPort = restPort;
			return restPort;
		}
	} catch (e) {
		console.warn("Failed to get Tauri REST port, falling back to 8081", e);
	}
	return 8081; // Fallback default
}

export async function callRestGateway(method: string, payload: any) {
	const restPort = await getRestPort();
	const maxRetries = 3;
	let attempt = 0;
	let delay = 500; // start backoff delay at 500ms

	let timeoutMs = 30000; // default 30s timeout
	if (
		method.includes("GenerateReport") ||
		method.includes("GenerateReportBundle")
	) {
		timeoutMs = 600000; // 10 minutes timeout for PDF generation
	} else if (
		method.includes("ValidateMeet") ||
		method.includes("PublishMeetData")
	) {
		timeoutMs = 60000; // 1 minute timeout for validation/publishing
	}

	while (true) {
		attempt++;
		const controller = new AbortController();
		const timeoutId = setTimeout(() => {
			controller.abort();
		}, timeoutMs);

		try {
			let userId = "desktop-user";
			if (typeof document !== "undefined") {
				const match = document.cookie.match(/(?:^|; )x-user-id=([^;]*)/);
				if (match) {
					userId = decodeURIComponent(match[1]);
				}
			}

			const response = await fetch(
				`http://localhost:${restPort}/api/grpc/${method}`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"x-user-id": userId,
					},
					body: JSON.stringify(payload),
					signal: controller.signal,
				},
			);

			if (!response.ok) {
				const text = await response.text();
				throw new Error(`REST Gateway error: ${text}`);
			}
			return await response.json();
		} catch (error: any) {
			const isTimeoutAbort = controller.signal.aborted;

			if (attempt >= maxRetries) {
				if (isTimeoutAbort) {
					throw new Error(
						`REST Gateway call to ${method} timed out after ${timeoutMs}ms`,
					);
				}
				throw error;
			}

			console.warn(
				`REST Gateway call to ${method} failed (attempt ${attempt}/${maxRetries}):`,
				error,
			);
			await new Promise((resolve) => setTimeout(resolve, delay));
			delay *= 2; // exponential backoff
		} finally {
			clearTimeout(timeoutId);
		}
	}
}

export async function downloadFile(
	filename: string,
	content: ArrayBuffer | string,
	isBase64 = false,
) {
	const isTauri =
		typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__;

	if (isTauri) {
		try {
			const { save } = await import("@tauri-apps/plugin-dialog");
			const { writeFile } = await import("@tauri-apps/plugin-fs");

			const savePath = await save({
				defaultPath: filename,
			});

			if (!savePath) {
				console.log("Download cancelled by user");
				return;
			}

			let bytes: Uint8Array;
			if (isBase64 && typeof content === "string") {
				const binaryString = window.atob(content);
				bytes = new Uint8Array(binaryString.length);
				for (let i = 0; i < binaryString.length; i++) {
					bytes[i] = binaryString.charCodeAt(i);
				}
			} else if (content instanceof ArrayBuffer) {
				bytes = new Uint8Array(content);
			} else if (typeof content === "string") {
				const encoder = new TextEncoder();
				bytes = encoder.encode(content);
			} else {
				throw new Error("Invalid content type for download");
			}

			await writeFile(savePath, bytes);
			console.log(`Successfully saved file to ${savePath}`);
		} catch (err) {
			console.error("Tauri file save failed:", err);
			throw err;
		}
	} else {
		// Browser fallback
		const link = document.createElement("a");
		if (isBase64 && typeof content === "string") {
			link.href = `data:application/octet-stream;base64,${content}`;
		} else if (content instanceof ArrayBuffer) {
			const blob = new Blob([content], { type: "application/octet-stream" });
			link.href = URL.createObjectURL(blob);
		} else {
			const blob = new Blob([content], { type: "text/plain" });
			link.href = URL.createObjectURL(blob);
		}
		link.download = filename;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		if (!(content instanceof String) && typeof content !== "string") {
			URL.revokeObjectURL(link.href);
		}
	}
}
