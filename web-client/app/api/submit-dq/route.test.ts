import { cookies, headers } from "next/headers";
import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as dqDb from "@/lib/dq-db";
import client from "@/lib/mm-client";
import { POST } from "./route";

vi.mock("@/lib/dq-db", () => ({
	checkDqExists: vi.fn(),
	saveDq: vi.fn(),
}));

vi.mock("@/lib/mm-client", () => ({
	default: {
		syncDQs: vi.fn(),
	},
}));

vi.mock("next/headers", () => ({
	headers: vi.fn(),
	cookies: vi.fn(),
}));

vi.mock("next/cache", () => ({
	revalidatePath: vi.fn(),
}));

describe("POST /api/submit-dq", () => {
	const mockPayload = {
		clientDqId: "dq-124",
		client_id: "judge-1",
		event: 1,
		heat: 1,
		lane: 1,
		swimmer: 1,
		infraction_code: "1A",
		notes: "Test note",
	};

	beforeEach(() => {
		vi.resetAllMocks();
		process.env.DATA_ACCESS_TOKEN = "my-secret-token";
		vi.mocked(headers).mockResolvedValue({
			get: vi.fn().mockReturnValue("e2e-bypass-user"),
		} as any);
		vi.mocked(cookies).mockResolvedValue({
			get: vi.fn().mockReturnValue({ value: "e2e-bypass-user" }),
		} as any);
	});

	describe("Authentication", () => {
		it("should return 403 if token is missing", async () => {
			const req = new NextRequest("http://localhost/api/submit-dq", {
				method: "POST",
				body: JSON.stringify(mockPayload),
			});

			const res = await POST(req);
			expect(res.status).toBe(403);
			expect(dqDb.saveDq).not.toHaveBeenCalled();
		});

		it("should return 403 if token is invalid", async () => {
			const req = new NextRequest(
				"http://localhost/api/submit-dq?token=wrong-token",
				{
					method: "POST",
					body: JSON.stringify(mockPayload),
				},
			);

			const res = await POST(req);
			expect(res.status).toBe(403);
		});

		it("should allow access with correct token", async () => {
			const req = new NextRequest(
				"http://localhost/api/submit-dq?token=my-secret-token",
				{
					method: "POST",
					body: JSON.stringify(mockPayload),
				},
			);

			vi.mocked(dqDb.checkDqExists).mockResolvedValue(false);
			vi.mocked(client.syncDQs).mockResolvedValue({
				success: true,
				message: "OK",
				updatedCount: 1,
			});

			const res = await POST(req);
			expect(res.status).toBe(200);
		});
	});

	describe("DQ Submission", () => {
		beforeEach(() => {
			vi.mocked(client.syncDQs).mockResolvedValue({
				success: true,
				message: "OK",
				updatedCount: 1,
			});
		});

		it("should return 400 if clientDqId is missing", async () => {
			const { clientDqId, ...invalidPayload } = mockPayload;
			const req = new NextRequest(
				"http://localhost/api/submit-dq?token=my-secret-token",
				{
					method: "POST",
					body: JSON.stringify(invalidPayload),
				},
			);

			const res = await POST(req);
			expect(res.status).toBe(400);
		});

		it("should return 200 if DQ already exists (idempotency)", async () => {
			const req = new NextRequest(
				"http://localhost/api/submit-dq?token=my-secret-token",
				{
					method: "POST",
					body: JSON.stringify(mockPayload),
				},
			);

			vi.mocked(dqDb.checkDqExists).mockResolvedValue(true);

			const res = await POST(req);
			const data = await res.json();

			expect(res.status).toBe(200);
			expect(data.message).toContain("already submitted");
			expect(dqDb.saveDq).not.toHaveBeenCalled();
		});

		it("should save the DQ and return success", async () => {
			const req = new NextRequest(
				"http://localhost/api/submit-dq?token=my-secret-token",
				{
					method: "POST",
					body: JSON.stringify(mockPayload),
				},
			);

			vi.mocked(dqDb.checkDqExists).mockResolvedValue(false);
			vi.mocked(dqDb.saveDq).mockResolvedValueOnce();

			const res = await POST(req);
			const data = await res.json();

			expect(res.status).toBe(200);
			expect(data.success).toBe(true);
			expect(dqDb.saveDq).toHaveBeenCalledWith(
				"dq-124",
				{
					client_id: "judge-1",
					event: 1,
					heat: 1,
					lane: 1,
					swimmer: 1,
					infraction_code: "1A",
					notes: "Test note",
				},
				"e2e-bypass-user",
			);
		});

		it("should default client_id to Unknown if missing", async () => {
			const { client_id, ...payload } = mockPayload;
			const req = new NextRequest(
				"http://localhost/api/submit-dq?token=my-secret-token",
				{
					method: "POST",
					body: JSON.stringify(payload),
				},
			);

			vi.mocked(dqDb.checkDqExists).mockResolvedValue(false);

			const res = await POST(req);
			expect(res.status).toBe(200);
			expect(dqDb.saveDq).toHaveBeenCalledWith(
				"dq-124",
				{
					client_id: "Unknown",
					event: 1,
					heat: 1,
					lane: 1,
					swimmer: 1,
					infraction_code: "1A",
					notes: "Test note",
				},
				"e2e-bypass-user",
			);
		});
	});
});
