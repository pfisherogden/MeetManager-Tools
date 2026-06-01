import { revalidatePath } from "next/cache";
import { type NextRequest, NextResponse } from "next/server";
import { corsOptions, withCors } from "@/lib/cors";
import { checkDqExists, saveDq } from "@/lib/dq-db";
import client from "@/lib/mm-client";

export async function OPTIONS() {
	return corsOptions();
}

export async function POST(request: NextRequest) {
	try {
		const { searchParams } = new URL(request.url);
		const token =
			request.headers.get("x-data-access-token") ||
			searchParams.get("token") ||
			"";

		const headerUserId = request.headers.get("x-user-id");
		const paramUid = searchParams.get("uid");
		const userId = headerUserId || paramUid || "e2e-bypass-user";

		if (process.env.NODE_ENV !== "production") {
			console.log(
				`API SUBMIT-DQ: Received request. UserID: ${userId}, Token Provided: ${token ? "YES" : "NO"}`,
			);
		}

		// Basic security check
		const configuredToken = process.env.DATA_ACCESS_TOKEN;
		const isTokenConfigured =
			configuredToken !== undefined && configuredToken !== "";
		const isAuthorized = !isTokenConfigured || token === configuredToken;

		if (!isAuthorized) {
			console.warn(
				`API SUBMIT-DQ: Unauthorized access attempt. UserID: ${userId}`,
			);
			return withCors(
				NextResponse.json({ error: "Unauthorized access" }, { status: 403 }),
			);
		}

		const payload = await request.json();
		const {
			clientDqId,
			client_id,
			event,
			heat,
			lane,
			swimmer,
			infraction_code,
			notes,
		} = payload;

		console.log(
			`API SUBMIT-DQ: Processing payload for clientDqId: ${clientDqId}, Judge: ${client_id}, UserID: ${userId}`,
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
		const exists = await checkDqExists(clientDqId, userId);
		if (exists) {
			return withCors(
				NextResponse.json(
					{ success: true, message: "DQ already submitted" },
					{ status: 200 },
				),
			);
		}

		// Save the new DQ to Firestore (Stateless storage)
		await saveDq(
			clientDqId,
			{
				client_id: client_id || "Unknown",
				event,
				heat,
				lane,
				swimmer,
				infraction_code,
				notes: notes || "",
			},
			userId,
		);

		// Ensure the volunteer page is revalidated
		revalidatePath("/dqs");

		// Trigger backend sync to MDB (Stateful storage)
		try {
			await client.syncDQs({
				dqsJson: JSON.stringify([payload]),
				uid: userId || "",
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
