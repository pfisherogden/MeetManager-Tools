import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as dqDb from "@/lib/dq-db";
import { POST } from "./route";

vi.mock("@/lib/dq-db", () => ({
	checkDqExists: vi.fn(),
	saveDq: vi.fn(),
}));

describe("POST /api/submit-dq", () => {
	const validToken = "mmtools-default-secret-2024";

	beforeEach(() => {
		vi.clearAllMocks();
		process.env.DATA_ACCESS_TOKEN = validToken;
	});

	it("returns 500 when DATA_ACCESS_TOKEN is not set", async () => {
		delete process.env.DATA_ACCESS_TOKEN;

		const req = new NextRequest(
			"http://localhost/api/submit-dq?token=invalid",
			{
				method: "POST",
				body: JSON.stringify({}),
			},
		);

		const res = await POST(req);
		expect(res.status).toBe(500);
	});

	it("returns 403 on invalid token", async () => {
		const req = new NextRequest(
			"http://localhost/api/submit-dq?token=invalid",
			{
				method: "POST",
				body: JSON.stringify({}),
			},
		);

		const res = await POST(req);
		expect(res.status).toBe(403);

		const json = await res.json();
		expect(json.error).toBe("Unauthorized access");
	});

	it("returns 400 on malformed payload (missing clientDqId)", async () => {
		const req = new NextRequest(
			`http://localhost/api/submit-dq?token=${validToken}`,
			{
				method: "POST",
				body: JSON.stringify({
					event: 1,
					heat: 1,
					lane: 1,
					swimmer: 1,
					infraction_code: "1A",
				}),
			},
		);

		const res = await POST(req);
		expect(res.status).toBe(400);

		const json = await res.json();
		expect(json.error).toBe("Missing clientDqId");
	});

	it("returns 400 on malformed payload (missing required fields)", async () => {
		const req = new NextRequest(
			`http://localhost/api/submit-dq?token=${validToken}`,
			{
				method: "POST",
				body: JSON.stringify({ clientDqId: "123" }), // Missing event, heat, swimmer, infraction_code
			},
		);

		const res = await POST(req);
		expect(res.status).toBe(400);

		const json = await res.json();
		expect(json.error).toBe("Malformed payload: missing required fields");
	});

	it("returns 200 OK and skips creation when clientDqId exists (idempotency)", async () => {
		vi.mocked(dqDb.checkDqExists).mockResolvedValueOnce(true);

		const req = new NextRequest(
			`http://localhost/api/submit-dq?token=${validToken}`,
			{
				method: "POST",
				body: JSON.stringify({
					clientDqId: "dq-123",
					event: 1,
					heat: 1,
					lane: 1,
					swimmer: 1,
					infraction_code: "1A",
				}),
			},
		);

		const res = await POST(req);
		expect(res.status).toBe(200);

		const json = await res.json();
		expect(json.success).toBe(true);
		expect(json.message).toBe("DQ already submitted");
		expect(dqDb.saveDq).not.toHaveBeenCalled();
	});

	it("returns 200 OK and creates DQ when clientDqId is new", async () => {
		vi.mocked(dqDb.checkDqExists).mockResolvedValueOnce(false);
		vi.mocked(dqDb.saveDq).mockResolvedValueOnce();

		const payload = {
			clientDqId: "dq-124",
			event: 1,
			heat: 1,
			lane: 1,
			swimmer: 1,
			infraction_code: "1A",
		};

		const req = new NextRequest(
			`http://localhost/api/submit-dq?token=${validToken}`,
			{
				method: "POST",
				body: JSON.stringify(payload),
			},
		);

		const res = await POST(req);
		expect(res.status).toBe(200);

		const json = await res.json();
		expect(json.success).toBe(true);
		expect(json.message).toBe("DQ submitted successfully");

		expect(dqDb.saveDq).toHaveBeenCalledTimes(1);
		expect(dqDb.saveDq).toHaveBeenCalledWith("dq-124", {
			event: 1,
			heat: 1,
			lane: 1,
			swimmer: 1,
			infraction_code: "1A",
		});
	});

	it("returns 500 on database error", async () => {
		vi.mocked(dqDb.checkDqExists).mockRejectedValueOnce(
			new Error("DB Connection Error"),
		);

		const req = new NextRequest(
			`http://localhost/api/submit-dq?token=${validToken}`,
			{
				method: "POST",
				body: JSON.stringify({
					clientDqId: "dq-125",
					event: 1,
					heat: 1,
					lane: 1,
					swimmer: 1,
					infraction_code: "1A",
				}),
			},
		);

		const res = await POST(req);
		expect(res.status).toBe(500);

		const json = await res.json();
		expect(json.error).toBe("Internal server error");
	});
});
