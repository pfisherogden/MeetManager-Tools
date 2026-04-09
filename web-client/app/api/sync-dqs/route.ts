import { type NextRequest, NextResponse } from "next/server";
import { corsOptions, withCors } from "@/lib/cors";
import client from "@/lib/mm-client";

export async function OPTIONS() {
	return corsOptions();
}

export async function POST(request: NextRequest) {
	const { searchParams } = new URL(request.url);
	const token = searchParams.get("token");
	const uid = searchParams.get("uid");

	// Basic security check
	const configuredToken = process.env.DATA_ACCESS_TOKEN;
	const isTokenConfigured =
		configuredToken !== undefined && configuredToken !== "";
	const isAuthorized = !isTokenConfigured || token === configuredToken;

	if (!isAuthorized) {
		return withCors(
			NextResponse.json({ error: "Unauthorized access" }, { status: 403 }),
		);
	}

	try {
		const dqs = await request.json();
		const dqsJson = JSON.stringify(dqs);

		const response = await client.syncDQs({
			dqsJson,
			uid: uid || "",
			accessToken: configuredToken || "",
		});

		if (response.success) {
			return withCors(
				NextResponse.json({ success: true, message: response.message }),
			);
		}
		return withCors(
			NextResponse.json(
				{ success: false, message: response.message },
				{ status: 500 },
			),
		);
	} catch (error: any) {
		console.error("API Error (sync-dqs):", error);
		return withCors(
			NextResponse.json(
				{ success: false, message: error.message },
				{ status: 500 },
			),
		);
	}
}
