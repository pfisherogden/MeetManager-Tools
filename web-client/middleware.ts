import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

export function middleware(request: NextRequest) {
	const { pathname } = request.nextUrl;

	// Respect AUTH_DISABLED setting for local dev/E2E
	const isAuthDisabled =
		process.env.NEXT_PUBLIC_AUTH_DISABLED === "true" ||
		process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true";

	if (process.env.NODE_ENV !== "production") {
		console.log(
			`[Middleware] Path: ${pathname}, AuthDisabled: ${isAuthDisabled}, E2EBypass: ${process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS}`,
		);
	}

	if (isAuthDisabled) {
		return NextResponse.next();
	}
	// Define public paths that don't require authentication
	const isPublicPath =
		pathname === "/login" ||
		pathname === "/login/" ||
		pathname.startsWith("/judge") ||
		pathname.startsWith("/api/test") ||
		pathname.startsWith("/api/submit-dq") ||
		pathname.startsWith("/api/data") || // Allow public data access for judge app
		pathname.startsWith("/_next") ||
		pathname.includes("/favicon.ico");

	if (isPublicPath) {
		return NextResponse.next();
	}

	// Check for the presence of the idToken cookie
	const idToken = request.cookies.get("idToken")?.value;

	if (!idToken) {
		// Redirect to login if not authenticated
		const loginUrl = new URL("/login", request.url);
		loginUrl.searchParams.set("returnUrl", pathname);
		return NextResponse.redirect(loginUrl);
	}

	return NextResponse.next();
}

export const config = {
	matcher: [
		/*
		 * Match all request paths except for the ones starting with:
		 * - api (API routes)
		 * - _next/static (static files)
		 * - _next/image (image optimization files)
		 * - favicon.ico (favicon file)
		 */
		"/((?!api/test|api/submit-dq|api/data|_next/static|_next/image|favicon.ico).*)",
	],
};
