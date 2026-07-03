import { NextRequest } from "next/server";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import client from "@/lib/mm-client";
import { GET } from "./route";

vi.mock("@/lib/mm-client", () => ({
	default: {
		getFile: vi.fn(),
	},
}));

describe("GET /api/data", () => {
	const originalEnv = process.env;

	beforeEach(() => {
		process.env = { ...originalEnv };
		vi.clearAllMocks();
	});

	afterAll(() => {
		process.env = originalEnv;
	});

	it("returns 400 if path is missing", async () => {
		const req = new NextRequest("http://localhost/api/data?token=test");
		const res = await GET(req);
		expect(res.status).toBe(400);
	});

	describe("when DATA_ACCESS_TOKEN is configured", () => {
		beforeEach(() => {
			process.env.DATA_ACCESS_TOKEN = "my-secret-token";
		});

		it("returns 403 if token is missing", async () => {
			const req = new NextRequest("http://localhost/api/data?path=test.json");
			const res = await GET(req);
			expect(res.status).toBe(403);
		});

		it("returns 403 if token is incorrect", async () => {
			const req = new NextRequest(
				"http://localhost/api/data?path=test.json&token=wrong",
			);
			const res = await GET(req);
			expect(res.status).toBe(403);
		});

		it("calls getFile and returns response if token is correct", async () => {
			vi.mocked(client.getFile).mockResolvedValue({
				content: new Uint8Array([1, 2, 3]),
				mimeType: "application/json",
			});

			const req = new NextRequest(
				"http://localhost/api/data?path=test.json&token=my-secret-token",
			);
			const res = await GET(req);
			expect(res.status).toBe(200);
			expect(client.getFile).toHaveBeenCalledWith({
				path: "test.json",
				token: "my-secret-token",
			});
		});
	});

	describe("when DATA_ACCESS_TOKEN is missing or empty", () => {
		it("allows access with the default fallback token", async () => {
			delete process.env.DATA_ACCESS_TOKEN;
			vi.mocked(client.getFile).mockResolvedValue({
				content: new Uint8Array([1, 2, 3]),
				mimeType: "application/json",
			});

			const req = new NextRequest(
				"http://localhost/api/data?path=test.json&token=mmtools-default-secret-2024",
			);
			const res = await GET(req);
			expect(res.status).toBe(200);
			expect(client.getFile).toHaveBeenCalledWith({
				path: "test.json",
				token: "mmtools-default-secret-2024",
			});
		});

		it("rejects access with an empty token", async () => {
			process.env.DATA_ACCESS_TOKEN = "";

			const req = new NextRequest("http://localhost/api/data?path=test.json");
			const res = await GET(req);
			expect(res.status).toBe(403);
			expect(client.getFile).not.toHaveBeenCalled();
		});

		it("rejects access with a random token", async () => {
			delete process.env.DATA_ACCESS_TOKEN;

			const req = new NextRequest(
				"http://localhost/api/data?path=test.json&token=random",
			);
			const res = await GET(req);
			expect(res.status).toBe(403);
			expect(client.getFile).not.toHaveBeenCalled();
		});
	});
});
