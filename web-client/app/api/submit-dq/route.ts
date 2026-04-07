import { type NextRequest, NextResponse } from "next/server";
import { checkDqExists, saveDq } from "@/lib/dq-db";

export async function POST(request: NextRequest) {
	const { searchParams } = new URL(request.url);
	const token = searchParams.get("token");

	// Basic security check
	const secretToken = process.env.DATA_ACCESS_TOKEN;

	if (!secretToken) {
		console.error("CRITICAL: DATA_ACCESS_TOKEN environment variable is missing.");
		return NextResponse.json({ error: "Internal server error" }, { status: 500 });
	}

	if (token !== secretToken) {
		return NextResponse.json({ error: "Unauthorized access" }, { status: 403 });
	}

	try {
		const payload = await request.json();
		const { clientDqId, event, heat, lane, swimmer, infraction_code } = payload;

		if (!clientDqId) {
			return NextResponse.json(
				{ error: "Missing clientDqId" },
				{ status: 400 },
			);
		}
		if (
			event === undefined ||
			heat === undefined ||
			swimmer === undefined ||
			infraction_code === undefined
		) {
			return NextResponse.json(
				{ error: "Malformed payload: missing required fields" },
				{ status: 400 },
			);
		}

		// Idempotency check
		const exists = await checkDqExists(clientDqId);
		if (exists) {
			return NextResponse.json(
				{ success: true, message: "DQ already submitted" },
				{ status: 200 },
			);
		}

		// Save the new DQ
		await saveDq(clientDqId, {
			event,
			heat,
			lane,
			swimmer,
			infraction_code,
		});

		return NextResponse.json({ success: true, message: "DQ submitted successfully" });
	} catch (error: any) {
		console.error("API Error (submit-dq):", error);
		return NextResponse.json(
			{ error: "Internal server error" },
			{ status: 500 },
		);
	}
}
