import { invoke } from "@tauri-apps/api/core";

let cachedRestPort: number | null = null;

async function getRestPort(): Promise<number> {
	if (cachedRestPort !== null) return cachedRestPort;
	try {
		if (typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__) {
			const [_grpcPort, restPort] =
				await invoke<[number, number]>("get_backend_ports");
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
	const response = await fetch(
		`http://localhost:${restPort}/api/grpc/${method}`,
		{
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"x-user-id": "desktop-user", // Desktop mode runs with local/mock auth credentials
			},
			body: JSON.stringify(payload),
		},
	);

	if (!response.ok) {
		const text = await response.text();
		throw new Error(`REST Gateway error: ${text}`);
	}
	return response.json();
}
