export interface SessionCookiePayload {
	idToken?: string;
	uid?: string;
	googleAccessToken?: string;
}

interface CookieReader {
	get(name: string): { value: string } | undefined;
}

/**
 * Parses the Firebase Hosting-compatible `__session` JSON cookie payload.
 * Firebase Hosting CDN strips all cookies except `__session` when proxying
 * requests to Cloud Run services.
 */
export function parseSessionCookie(raw?: string | null): SessionCookiePayload {
	if (!raw) return {};
	for (const candidate of [raw, tryDecodeURIComponent(raw)]) {
		if (!candidate) continue;
		try {
			const parsed = JSON.parse(candidate);
			if (parsed && typeof parsed === "object") {
				return parsed as SessionCookiePayload;
			}
		} catch {
			// Ignore malformed cookie JSON
		}
	}
	return {};
}

function tryDecodeURIComponent(val: string): string | null {
	try {
		return decodeURIComponent(val);
	} catch {
		return null;
	}
}

/**
 * Reads `idToken`, `x-user-id`, or `googleAccessToken` from a Next.js cookieStore,
 * falling back to the Firebase Hosting `__session` cookie when individual cookies
 * have been stripped by the Firebase Hosting CDN proxy.
 */
export function getServerCookie(
	cookieStore: CookieReader,
	name: "idToken" | "x-user-id" | "googleAccessToken",
): string | undefined {
	const direct = cookieStore.get(name)?.value;
	if (direct) return direct;

	const sessionRaw = cookieStore.get("__session")?.value;
	if (!sessionRaw) return undefined;

	const parsed = parseSessionCookie(sessionRaw);
	if (name === "idToken") return parsed.idToken;
	if (name === "x-user-id") return parsed.uid;
	if (name === "googleAccessToken") return parsed.googleAccessToken;
	return undefined;
}
