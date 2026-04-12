import { type NextRequest, NextResponse } from "next/server";
import { corsOptions, withCors } from "@/lib/cors";
import { checkDqExists, saveDq } from "@/lib/dq-db";
import client from "@/lib/mm-client";

export async function OPTIONS() {
	return corsOptions();
}

export async function POST(request: NextRequest) {
	const { searchParams } = new URL(request.url);
	const token = searchParams.get("token");
	const uid = searchParams.get("uid");

	console.log(
		`API SUBMIT-DQ: Received request. UID: ${uid}, Token Provided: ${token ? "YES" : "NO"}`,
	);

	// Basic security check
	const configuredToken = process.env.DATA_ACCESS_TOKEN;
	const isTokenConfigured =
		configuredToken !== undefined && configuredToken !== "";
	const isAuthorized = !isTokenConfigured || token === configuredToken;

	if (!isAuthorized) {
		console.warn(`API SUBMIT-DQ: Unauthorized access attempt. UID: ${uid}`);
		return withCors(
			NextResponse.json({ error: "Unauthorized access" }, { status: 403 }),
		);
	}

	try {
		const payload = await request.json();
		const { clientDqId, event, heat, lane, swimmer, infraction_code } = payload;

		console.log(
			`API SUBMIT-DQ: Processing payload for clientDqId: ${clientDqId}`,
		);

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

		// Save the new DQ to Firestore (Stateless storage)
		await saveDq(clientDqId, {
			event,
			heat,
			lane,
			swimmer,
			infraction_code,
		});

		// Trigger backend sync to MDB (Stateful storage)
		// We wrap it in a try-catch to avoid failing the whole request if backend is down,
		// though idempotency allows the client to retry.
		try {
			const syncPayload = [
				{
					event_id: event,
					swimmer_id: swimmer, // This might be name or ID depending on app version
					dq_code: infraction_code,
					heat: heat,
					lane: lane,
					timestamp: new Date().toISOString(),
				},
			];
			await client.syncDQs({
				dqsJson: JSON.stringify(syncPayload),
				uid: uid || "",
				accessToken: configuredToken || "",
			});
		} catch (syncError) {
			console.error("Failed to trigger backend sync for DQ:", syncError);
			// We still return 200 because it's saved in Firestore and can be synced later
		}

		return NextResponse.json({
			success: true,
			message: "DQ submitted successfully",
		});
	} catch (error: any) {
		console.error("API Error (submit-dq):", error);
		return NextResponse.json(
			{ error: "Internal server error" },
			{ status: 500 },
		);
	}
}
