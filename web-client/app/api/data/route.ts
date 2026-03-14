import { type NextRequest, NextResponse } from "next/server";
import client from "@/lib/mm-client";

export async function GET(request: NextRequest) {
	const { searchParams } = new URL(request.url);
	const path = searchParams.get("path");

	if (!path) {
		return NextResponse.json({ error: "Path is required" }, { status: 400 });
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
