import { NextRequest } from "next/server";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import client from "@/lib/mm-client";
import { POST } from "./route";

vi.mock("@/lib/mm-client", () => ({
	default: {
		syncDQs: vi.fn(),
	},
}));

describe("POST /api/sync-dqs", () => {
	const originalEnv = process.env;

	beforeEach(() => {
		vi.resetModules();
		process.env = { ...originalEnv };
		vi.clearAllMocks();
	});

	afterAll(() => {
		process.env = originalEnv;
	});

	describe("when DATA_ACCESS_TOKEN is configured", () => {
		beforeEach(() => {
			process.env.DATA_ACCESS_TOKEN = "my-secret-token";
		});

		it("returns 403 if token is missing", async () => {
			const req = new NextRequest("http://localhost/api/sync-dqs", {
				method: "POST",
				body: JSON.stringify([{ id: 1 }]),
			});
			const res = await POST(req);
			expect(res.status).toBe(403);
		});

		it("returns 403 if token is incorrect", async () => {
			const req = new NextRequest("http://localhost/api/sync-dqs?token=wrong", {
				method: "POST",
				body: JSON.stringify([{ id: 1 }]),
			});
			const res = await POST(req);
			expect(res.status).toBe(403);
		});

		it("calls syncDQs and returns 200 if token is correct", async () => {
			vi.mocked(client.syncDQs).mockResolvedValue({
				success: true,
				message: "Synced",
			});

			const req = new NextRequest(
				"http://localhost/api/sync-dqs?token=my-secret-token&uid=test-uid",
				{
					method: "POST",
					body: JSON.stringify([{ id: 1 }]),
				},
			);
			const res = await POST(req);
			expect(res.status).toBe(200);
			const json = await res.json();
			expect(json.success).toBe(true);
			expect(client.syncDQs).toHaveBeenCalledWith({
				dqsJson: '[{"id":1}]',
				uid: "test-uid",
				accessToken: "my-secret-token",
			});
		});
	});

	describe("when DATA_ACCESS_TOKEN is missing or empty (fallback mode)", () => {
		it("allows access without any token", async () => {
			delete process.env.DATA_ACCESS_TOKEN;
			vi.mocked(client.syncDQs).mockResolvedValue({
				success: true,
				message: "Synced",
			});

			const req = new NextRequest("http://localhost/api/sync-dqs", {
				method: "POST",
				body: JSON.stringify([{ id: 1 }]),
			});
			const res = await POST(req);
			expect(res.status).toBe(200);
			expect(client.syncDQs).toHaveBeenCalledWith({
				dqsJson: '[{"id":1}]',
				uid: "",
				accessToken: "",
			});
		});

		it("allows access with an empty token environment variable", async () => {
			process.env.DATA_ACCESS_TOKEN = "";
			vi.mocked(client.syncDQs).mockResolvedValue({
				success: true,
				message: "Synced",
			});

			const req = new NextRequest("http://localhost/api/sync-dqs", {
				method: "POST",
				body: JSON.stringify([{ id: 1 }]),
			});
			const res = await POST(req);
			expect(res.status).toBe(200);
			expect(client.syncDQs).toHaveBeenCalledWith({
				dqsJson: '[{"id":1}]',
				uid: "",
				accessToken: "",
			});
		});
	});
});
