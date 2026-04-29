import { type NextRequest, NextResponse } from "next/server";
import { Metadata } from "nice-grpc";
import client from "@/lib/mm-client";

/**
 * STRICTLY GATED: Internal E2E testing endpoint for direct data manipulation.
 * Only active when NEXT_PUBLIC_E2E_AUTH_BYPASS=true.
 */
export async function POST(request: NextRequest) {
	if (process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS !== "true") {
		return NextResponse.json({ error: "Access Denied" }, { status: 403 });
	}

	const { searchParams } = new URL(request.url);
	const action = searchParams.get("action");
	const uid = request.headers.get("x-user-id");

	if (!uid) {
		return NextResponse.json(
			{ error: "x-user-id header required" },
			{ status: 400 },
		);
	}

	const metadata = new Metadata();
	metadata.set("x-user-id", uid);
	metadata.set("authorization", "Bearer dev-token");

	try {
		if (action === "upload_dataset") {
			const body = await request.json();
			const { filename, data_json } = body;

			// Helper to simulate the stream generator for uploadDataset
			// IMPORTANT: First message MUST contain the filename if we want the backend to use it.
			async function* requestGenerator() {
				// Message 1: Metadata/Filename
				yield {
					filename,
				};
				// Message 2: Data
				yield {
					chunk: Buffer.from(data_json),
				};
			}

			const response = await client.uploadDataset(requestGenerator(), {
				metadata,
			});
			return NextResponse.json(response);
		}

		if (action === "set_active") {
			const { filename } = await request.json();
			const response = await client.setActiveDataset(
				{ filename },
				{ metadata },
			);
			return NextResponse.json(response);
		}

		if (action === "list_datasets") {
			const response = await client.listDatasets({}, { metadata });
			return NextResponse.json(response);
		}

		return NextResponse.json({ error: "Invalid action" }, { status: 400 });
	} catch (error: any) {
		console.error(`E2E TEST API ERROR (${action}):`, error);
		return NextResponse.json({ error: error.message }, { status: 500 });
	}
}

export async function GET(request: NextRequest) {
	return POST(request);
}
