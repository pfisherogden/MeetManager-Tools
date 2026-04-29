import { type NextRequest, NextResponse } from "next/server";
import client from "@/lib/mm-client";

export const dynamic = "force-dynamic";

export async function GET(_request: NextRequest) {
	try {
		console.log("TEST-BUNDLE: Starting generation with sample data...");

		const reports = [
			{ type: 4, title: "Meet Program" },
			{ type: 9, title: "Judge Sheets" },
			{ type: 8, title: "Timer Sheets" },
		];

		const response = await client.generateReportBundle({
			reports: reports.map((r) => ({
				...r,
				teamFilter: "",
				genderFilter: "",
				ageGroupFilter: "",
				columnsOnPage: 2,
				showRelaySwimmers: true,
				zebraStriping: true,
				rendererType: 0, // RENDERER_TYPE_UNSPECIFIED
				htmlPreview: false,
			})),
			bundleName: "test_sample_bundle.zip",
			rendererType: 0, // RENDERER_TYPE_UNSPECIFIED
		});

		if (!response.success) {
			return NextResponse.json({ error: response.message }, { status: 500 });
		}

		// Security: Do NOT include the DATA_ACCESS_TOKEN in the public JSON response.
		// The frontend/caller should use the returned bundleUrl which points to the sample-user's data.
		// Since we've enabled unauthenticated access for 'sample-user' in the backend for these specific paths,
		// we don't need to append the token here.

		const cleanBundleUrl = response.bundleUrl?.split("&token=")[0];

		return NextResponse.json({
			success: true,
			message: "Test bundle generated successfully for sample data",
			downloadUrl: cleanBundleUrl,
			filename: response.filename,
			instructions:
				"To download, append your session token if needed, or use the unauthenticated sample path if enabled.",
		});
	} catch (error: any) {
		console.error("TEST-BUNDLE ERROR:", error);
		return NextResponse.json({ error: error.message }, { status: 500 });
	}
}
