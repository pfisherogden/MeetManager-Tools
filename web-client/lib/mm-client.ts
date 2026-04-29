import {
	ChannelCredentials,
	createChannel,
	createClientFactory,
	Metadata,
} from "nice-grpc";
import {
	type MeetManagerServiceClient,
	MeetManagerServiceDefinition,
} from "./proto/meetmanager/v1/meet_manager";

// Determine host:
// - Server Side (Docker): use 'backend:8080' (or env var)
// - Client Side (Browser): use 'localhost:8081' (or env var for CI/Tunnels)
let rawHost = "backend:8080";

if (typeof window === "undefined") {
	// Server-side: hit the backend service directly on its internal port
	rawHost =
		process.env.BACKEND_URL ||
		process.env.BACKEND_INTERNAL_HOST ||
		"backend:8080";
} else {
	// Client-side (Browser): hit the backend through the host-mapped port
	// Use NEXT_PUBLIC_BACKEND_PORT if provided (defaults to 8081 for local dev/ssh-tunnel bypass)
	const port = process.env.NEXT_PUBLIC_BACKEND_PORT || "8081";
	rawHost = `localhost:${port}`;
}

console.log(
	`E2E DEBUG: mm-client connecting to rawHost: ${rawHost} (Mode: ${typeof window === "undefined" ? "Server" : "Client"})`,
);

// Strip protocol if present (e.g. from http://backend:8080)
const host = rawHost.replace(/^https?:\/\//, "");
console.log(`E2E DEBUG: mm-client channel host: ${host}`);

// Create a middleware to add the token and x-user-id to every request
const authMiddleware = async function* (call: any, options: any) {
	let token: string | undefined;
	let userId: string | undefined;

	if (typeof window === "undefined") {
		// Server-side: Import dynamically to avoid client-side bundling issues
		try {
			const { cookies } = await import("next/headers");
			const cookieStore = await cookies();
			token = cookieStore.get("idToken")?.value;
			userId = cookieStore.get("x-user-id")?.value;
		} catch (e) {
			console.warn("Could not retrieve cookies on server", e);
		}
	} else {
		// Client-side: use js-cookie if needed, or simple regex
		const idTokenMatch = document.cookie.match(/idToken=([^;]+)/);
		if (idTokenMatch) token = idTokenMatch[1];

		const userIdMatch = document.cookie.match(/x-user-id=([^;]+)/);
		if (userIdMatch) userId = userIdMatch[1];
	}

	let metadata = Metadata(options.metadata);
	if (token) metadata = metadata.set("Authorization", `Bearer ${token}`);
	if (userId) metadata = metadata.set("x-user-id", userId);

	// E2E Bypass: Force dev-token if none provided and bypass is active
	if (!token && process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true") {
		metadata = metadata.set("Authorization", "Bearer dev-token");
	}

	return yield* call.next(call.request, {
		...options,
		metadata,
	});
};

// Create a singleton client
const clientFactory = createClientFactory().use(authMiddleware);

// Use secure credentials if host implies cloud (contains .run.app) or via env var
const useSsl =
	host.includes(".run.app") || process.env.BACKEND_USE_SSL === "true";
const credentials = useSsl
	? ChannelCredentials.createSsl()
	: ChannelCredentials.createInsecure();

const client: MeetManagerServiceClient = clientFactory.create(
	MeetManagerServiceDefinition,
	createChannel(host, credentials, {
		"grpc.max_receive_message_length": 50 * 1024 * 1024,
		"grpc.max_send_message_length": 50 * 1024 * 1024,
	}),
	{
		"*": {
			timeout: 300000, // 5 minutes
		},
	},
);

export default client;
