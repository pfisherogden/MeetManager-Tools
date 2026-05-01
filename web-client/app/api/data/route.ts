import { type NextRequest, NextResponse } from "next/server";
import { corsOptions, withCors } from "@/lib/cors";
import client from "@/lib/mm-client";

export async function OPTIONS() {
	return corsOptions();
}

export async function GET(request: NextRequest) {
	const { searchParams } = new URL(request.url);
	const path = searchParams.get("path");
	const token = searchParams.get("token");

	if (!path) {
		return withCors(
			NextResponse.json({ error: "Path is required" }, { status: 400 }),
		);
	}

	// Basic security check: allow if token matches environment secret or if it's a public path
	const configuredToken =
		process.env.DATA_ACCESS_TOKEN || "mmtools-default-secret-2024";
	const isAuthorized =
		path.startsWith("users/sample-user/") || token === configuredToken;

	if (!isAuthorized) {
		console.warn(
			`[API/data] Unauthorized access attempt: path=${path}, tokenProvided=${token ? `YES (len=${token.length})` : "NO"}, tokenExpected=${configuredToken ? "YES" : "NO"}`,
		);
		return withCors(
			NextResponse.json({ error: "Unauthorized access" }, { status: 403 }),
		);
	}

	try {
		const response = await client.getFile({
			path,
			token: token || "",
		});

		const filename = path.split("/").pop() || "download";
		const isZip = filename.endsWith(".zip");

		return withCors(
			new NextResponse(response.content as any, {
				headers: {
					"Content-Type":
						response.mimeType ||
						(isZip ? "application/zip" : "application/octet-stream"),
					"Content-Disposition": `attachment; filename="${filename}"`,
					"Cache-Control": "public, max-age=3600",
				},
			}),
		);
	} catch (error: any) {
		const safePath = String(path).replace(/[^\w./-]/g, "");
		console.error(`API Error (data?path=${safePath}):`, error.message);
		return withCors(
			NextResponse.json(
				{ error: `Failed to fetch file: ${error.message}` },
				{ status: 500 },
			),
		);
	}
}
