import { type NextRequest, NextResponse } from "next/server";
import client from "@/lib/mm-client";

export async function GET(request: NextRequest) {
	const { searchParams } = new URL(request.url);
	const path = searchParams.get("path");
	const token = searchParams.get("token");

	// Basic security check: allow if token matches environment secret or if it's a public path
	const configuredToken = process.env.DATA_ACCESS_TOKEN;
	const isTokenConfigured = configuredToken !== undefined && configuredToken !== "";

	// Allow if no token is configured (fallback mode), OR if the configured token matches
	const isAuthorized = !isTokenConfigured || token === configuredToken;

	if (!path) {
		return NextResponse.json({ error: "Path is required" }, { status: 400 });
	}

	if (!isAuthorized) {
		return NextResponse.json({ error: "Unauthorized access" }, { status: 403 });
	}

	try {
		const response = await client.getFile({ path });

		return new NextResponse(response.content, {
			headers: {
				"Content-Type": response.mimeType,
				"Cache-Control": "public, max-age=3600",
			},
		});
	} catch (error: any) {
		console.error(`API Error (data?path=${path}):`, error);
		return NextResponse.json(
			{ error: `Failed to fetch file: ${error.message}` },
			{ status: 500 },
		);
	}
}
