import { NextResponse } from "next/server";

/**
 * E2E-only endpoint to synthesize a valid mock session.
 * This sets the cookies that getAuthMetadata and AuthProvider expect.
 */
export async function GET(request: Request) {
	if (process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS !== "true") {
		return new NextResponse("Not Found", { status: 404 });
	}

	const { searchParams } = new URL(request.url);
	const mockUid = searchParams.get("uid") || "e2e-bypass-user";

	console.log(`[API Test Auth] Performing mock login for UID: ${mockUid}`);

	const response = NextResponse.json({ success: true, uid: mockUid });

	response.cookies.set("idToken", "dev-token", {
		httpOnly: true,
		secure: false,
		sameSite: "strict",
		path: "/",
	});

	response.cookies.set("x-user-id", mockUid, {
		httpOnly: false,
		secure: false,
		sameSite: "strict",
		path: "/",
	});

	return response;
}

export async function POST(request: Request) {
	return GET(request);
}
