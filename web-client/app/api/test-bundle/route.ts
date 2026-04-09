import { type NextRequest, NextResponse } from "next/server";
import client from "@/lib/mm-client";

export const dynamic = "force-dynamic";

export async function GET(_request: NextRequest) {
	try {
		console.log("TEST-BUNDLE: Starting generation with sample data...");

		// We use a dummy metadata since we're bypassing auth via the backend sample-data logic
		// Or better: the backend GenerateReportBundle should support a special case for sample data
		// But for now, we'll just try to trigger it.
		// Note: The backend GenerateReportBundle currently requires auth.
		// I will need to update the backend to allow GenerateReportBundle for Sample_Data.json statelessly.

		const reports = [
			{ type: 4, title: "Meet Program" },
			{ type: 9, title: "Judge Sheets" },
			{ type: 8, title: "Timer Sheets" },
		];

		// We pass a special token or rely on the backend being updated
		const _token = process.env.DATA_ACCESS_TOKEN || "";

		const response = await client.generateReportBundle({
			reports: reports.map((r) => ({
				...r,
				teamFilter: "",
				genderFilter: "",
				ageGroupFilter: "",
				columnsOnPage: 2,
				showRelaySwimmers: true,
				zebraStriping: true,
			})),
			bundleName: "test_sample_bundle.zip",
		});

		if (!response.success) {
			return NextResponse.json({ error: response.message }, { status: 500 });
		}

		return NextResponse.json({
			success: true,
			message: "Test bundle triggered successfully",
			bundleUrl: response.bundleUrl,
			filename: response.filename,
		});
	} catch (error: any) {
		console.error("TEST-BUNDLE ERROR:", error);
		return NextResponse.json({ error: error.message }, { status: 500 });
	}
}
