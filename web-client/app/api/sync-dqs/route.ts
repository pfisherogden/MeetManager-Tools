import { type NextRequest, NextResponse } from "next/server";
import client from "@/lib/mm-client";

export async function POST(request: NextRequest) {
	const { searchParams } = new URL(request.url);
	const token = searchParams.get("token");

	// Basic security check
	const secretToken =
		process.env.DATA_ACCESS_TOKEN || "mmtools-default-secret-2024";
	if (token !== secretToken) {
		return NextResponse.json({ error: "Unauthorized access" }, { status: 403 });
	}

	try {
		const dqs = await request.json();
		const dqsJson = JSON.stringify(dqs);

		const response = await client.syncDQs({ dqsJson });

		if (response.success) {
			return NextResponse.json({ success: true, message: response.message });
		}
		return NextResponse.json(
			{ success: false, message: response.message },
			{ status: 500 },
		);
	} catch (error: any) {
		console.error("API Error (sync-dqs):", error);
		return NextResponse.json(
			{ success: false, message: error.message },
			{ status: 500 },
		);
	}
}
