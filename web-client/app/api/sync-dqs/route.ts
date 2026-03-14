import { type NextRequest, NextResponse } from "next/server";
import client from "@/lib/mm-client";

export async function POST(request: NextRequest) {
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
