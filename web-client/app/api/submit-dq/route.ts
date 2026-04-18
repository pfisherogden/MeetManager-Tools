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
		const {
			clientDqId,
			client_id,
			event,
			heat,
			lane,
			swimmer,
			infraction_code,
		} = payload;

		console.log(
			`API SUBMIT-DQ: Processing payload for clientDqId: ${clientDqId}, Judge: ${client_id}`,
		);

		if (!clientDqId) {
			return withCors(
				NextResponse.json({ error: "Missing clientDqId" }, { status: 400 }),
			);
		}
		if (
			event === undefined ||
			heat === undefined ||
			swimmer === undefined ||
			infraction_code === undefined
		) {
			return withCors(
				NextResponse.json(
					{ error: "Malformed payload: missing required fields" },
					{ status: 400 },
				),
			);
		}

		// Idempotency check
		const exists = await checkDqExists(clientDqId);
		if (exists) {
			return withCors(
				NextResponse.json(
					{ success: true, message: "DQ already submitted" },
					{ status: 200 },
				),
			);
		}

		// Save the new DQ to Firestore (Stateless storage)
		await saveDq(clientDqId, {
			client_id: client_id || "Unknown",
			event,
			heat,
			lane,
			swimmer,
			infraction_code,
		});

		// Trigger backend sync to MDB (Stateful storage)
		try {
			await client.syncDQs({
				dqsJson: JSON.stringify([payload]),
				uid: uid || "",
				accessToken: token || "",
			});
		} catch (syncError) {
			console.error("Failed to trigger backend sync for DQ:", syncError);
		}

		return withCors(
			NextResponse.json({
				success: true,
				message: "DQ submitted successfully",
			}),
		);
	} catch (error: any) {
		console.error("API Error (submit-dq):", error);
		return withCors(
			NextResponse.json({ error: "Internal server error" }, { status: 500 }),
		);
	}
}
