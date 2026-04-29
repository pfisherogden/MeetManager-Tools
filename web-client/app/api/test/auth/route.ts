import { cookies } from "next/headers";
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
	const cookieStore = await cookies();

	console.log(`[API Test Auth] Performing mock login for UID: ${mockUid}`);

	cookieStore.set("idToken", "dev-token", {
		httpOnly: true,
		secure: process.env.NODE_ENV === "production",
		sameSite: "strict",
		path: "/",
	});

	cookieStore.set("x-user-id", mockUid, {
		httpOnly: false,
		secure: process.env.NODE_ENV === "production",
		sameSite: "strict",
		path: "/",
	});

	return NextResponse.json({ success: true, uid: mockUid });
}
