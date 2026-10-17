import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUploadDataset = vi.fn();
const mockRevalidatePath = vi.fn();
const mockCookiesGet = vi.fn();
const mockHeadersGet = vi.fn();

vi.mock("next/cache", () => ({
	revalidatePath: (...args: any[]) => mockRevalidatePath(...args),
}));

vi.mock("next/headers", () => ({
	cookies: vi.fn(async () => ({
		get: (key: string) => mockCookiesGet(key),
	})),
	headers: vi.fn(async () => ({
		get: (key: string) => mockHeadersGet(key),
	})),
}));

vi.mock("@/lib/mm-client", () => ({
	default: {
		uploadDataset: (...args: any[]) => mockUploadDataset(...args),
	},
}));

const mockCallRestGateway = vi.fn();

vi.mock("@/lib/tauri-bridge", () => ({
	getRestPort: vi.fn(async () => "8081"),
	isTauri: vi.fn(() => true),
	callRestGateway: (...args: any[]) => mockCallRestGateway(...args),
}));

describe("Google Drive Upload Actions (Server & Tauri Client)", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockHeadersGet.mockImplementation((key: string) =>
			key === "x-user-id" ? "test-user-123" : null,
		);
		mockCookiesGet.mockImplementation((key: string) => {
			if (key === "x-user-id") return { value: "test-user-123" };
			if (key === "googleAccessToken") return { value: "cookie-drive-token" };
			return undefined;
		});
	});

	describe("actions.server.ts (Local Web & Cloud Run)", () => {
		it("uploads pre-fetched base64 content via gRPC streaming uploadDataset", async () => {
			const { uploadDatasetFromDrive } = await import("./actions.server");
			const rawContent = Buffer.from(JSON.stringify({ meet: [] }));
			const base64Content = rawContent.toString("base64");

			const streamedChunks: Uint8Array[] = [];
			const streamedFilenames: string[] = [];
			mockUploadDataset.mockImplementation(async (gen: AsyncIterable<any>) => {
				for await (const req of gen) {
					if (req.filename) streamedFilenames.push(req.filename);
					if (req.chunk) streamedChunks.push(req.chunk);
				}
				return {
					success: true,
					message: "Uploaded from Drive",
					datasetPath: "/data/DriveMeet.json",
				};
			});

			const res = await uploadDatasetFromDrive(
				"drive-file-1",
				"DriveMeet.json",
				"explicit-token",
				base64Content,
			);

			expect(res.success).toBe(true);
			expect(streamedFilenames).toEqual(["DriveMeet.json"]);
			expect(Buffer.concat(streamedChunks).toString("utf8")).toBe(
				JSON.stringify({ meet: [] }),
			);
			expect(mockRevalidatePath).toHaveBeenCalledWith("/admin");
		});

		it("accepts single-object payload for multi-MB .mdb files (>1M base64 chars) and chunks at 1MB", async () => {
			const { uploadDatasetFromDrive } = await import("./actions.server");
			// 2.2 MB raw binary (> 2.9M base64 chars, exceeding React Flight's 1e6 array limit)
			const rawContent = Buffer.alloc(2.2 * 1024 * 1024, 0x41);
			const base64Content = rawContent.toString("base64");
			expect(base64Content.length).toBeGreaterThan(1_000_000);

			const streamedChunks: Uint8Array[] = [];
			const streamedFilenames: string[] = [];
			mockUploadDataset.mockImplementation(async (gen: AsyncIterable<any>) => {
				for await (const req of gen) {
					if (req.filename) streamedFilenames.push(req.filename);
					if (req.chunk) streamedChunks.push(req.chunk);
				}
				return {
					success: true,
					message: "Saved Singers23.mdb",
				};
			});

			const res = await uploadDatasetFromDrive({
				fileId: "drive-mdb-large",
				filename: "Singers23.mdb",
				accessToken: "explicit-token",
				contentBase64: base64Content,
			});

			expect(res.success).toBe(true);
			expect(streamedFilenames).toEqual(["Singers23.mdb"]);
			expect(streamedChunks.length).toBe(3); // 1MB + 1MB + 0.2MB
			expect(Buffer.concat(streamedChunks).length).toBe(rawContent.length);
		});

		it("downloads file from Google Drive API v3 when contentBase64 is not provided", async () => {
			const { uploadDatasetFromDrive } = await import("./actions.server");
			const drivePayload = new Uint8Array([0x00, 0x01, 0x02, 0x03]);
			const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
				new Response(drivePayload, {
					status: 200,
					headers: { "Content-Type": "application/octet-stream" },
				}),
			);

			const streamedChunks: Uint8Array[] = [];
			mockUploadDataset.mockImplementation(async (gen: AsyncIterable<any>) => {
				for await (const req of gen) {
					if (req.chunk) streamedChunks.push(req.chunk);
				}
				return {
					success: true,
					message: "MDB imported",
					datasetPath: "/data/Meet.mdb",
				};
			});

			const res = await uploadDatasetFromDrive(
				"drive-mdb-id",
				"Meet.mdb",
				"oauth-token-xyz",
			);

			expect(fetchSpy).toHaveBeenCalledWith(
				"https://www.googleapis.com/drive/v3/files/drive-mdb-id?alt=media&supportsAllDrives=true",
				{
					headers: {
						Authorization: "Bearer oauth-token-xyz",
					},
				},
			);
			expect(res.success).toBe(true);
			expect(Buffer.concat(streamedChunks)).toEqual(Buffer.from(drivePayload));
			fetchSpy.mockRestore();
		});

		it("returns descriptive error when Google Drive API returns 403", async () => {
			const { uploadDatasetFromDrive } = await import("./actions.server");
			const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
				new Response(
					JSON.stringify({
						error: { message: "The user has not granted the app read access" },
					}),
					{ status: 403 },
				),
			);

			const res = await uploadDatasetFromDrive(
				"restricted-file",
				"Secret.mdb",
				"expired-token",
			);

			expect(res.success).toBe(false);
			expect(res.message).toContain(
				"The user has not granted the app read access",
			);
			fetchSpy.mockRestore();
		});
	});

	describe("actions.client.ts (Tauri Desktop App)", () => {
		it("forwards pre-fetched base64 Drive content to REST Gateway UploadDataset", async () => {
			const { uploadDatasetFromDrive } =
				await vi.importActual<typeof import("./actions.client")>(
					"./actions.client",
				);
			mockCallRestGateway.mockResolvedValueOnce({
				success: true,
				message: "Saved via sidecar",
				datasetPath: "/tmp/TauriDrive.mdb",
			});

			const res = await uploadDatasetFromDrive({
				fileId: "tauri-drive-id",
				filename: "TauriDrive.mdb",
				accessToken: "tauri-token",
				contentBase64: "dGF1cmktZGF0YQ==",
			});

			expect(res.success).toBe(true);
			expect(mockCallRestGateway).toHaveBeenCalledWith("UploadDataset", {
				filename: "TauriDrive.mdb",
				content: "dGF1cmktZGF0YQ==",
			});
		});

		it("downloads from Drive API and uploads to REST Gateway when contentBase64 is omitted", async () => {
			const { uploadDatasetFromDrive } =
				await vi.importActual<typeof import("./actions.client")>(
					"./actions.client",
				);
			const fetchSpy = vi
				.spyOn(globalThis, "fetch")
				.mockResolvedValueOnce(
					new Response("mock-json-bytes", { status: 200 }),
				);
			mockCallRestGateway.mockResolvedValueOnce({
				success: true,
				message: "Saved via sidecar",
			});

			const res = await uploadDatasetFromDrive(
				"tauri-drive-2",
				"TauriMeet.json",
				"tauri-oauth-token",
			);

			expect(res.success).toBe(true);
			expect(fetchSpy).toHaveBeenCalledWith(
				"https://www.googleapis.com/drive/v3/files/tauri-drive-2?alt=media&supportsAllDrives=true",
				{
					headers: {
						Authorization: "Bearer tauri-oauth-token",
					},
				},
			);
			expect(mockCallRestGateway).toHaveBeenCalledWith("UploadDataset", {
				filename: "TauriMeet.json",
				content: Buffer.from("mock-json-bytes").toString("base64"),
			});
			fetchSpy.mockRestore();
		});

		it("returns safe fallback config from getGoogleConfig when sidecar is unreachable", async () => {
			const { getGoogleConfig } =
				await vi.importActual<typeof import("./actions.client")>(
					"./actions.client",
				);
			mockCallRestGateway.mockRejectedValueOnce(
				new Error("Connection refused"),
			);

			const config = await getGoogleConfig();
			expect(config).not.toBeNull();
			expect(config).toHaveProperty("apiKey");
			expect(config).toHaveProperty("appId");
		});
	});
});
