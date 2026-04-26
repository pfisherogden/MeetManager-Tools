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

// Create a middleware to add the token to every request
const authMiddleware = async function* (call: any, options: any) {
	let token: string | undefined;

	if (typeof window === "undefined") {
		// Server-side: Import dynamically to avoid client-side bundling issues
		try {
			const { cookies } = await import("next/headers");
			const cookieStore = await cookies();
			token = cookieStore.get("idToken")?.value;
		} catch (e) {
			console.warn("Could not retrieve cookies on server", e);
		}
	} else {
		// Client-side: use js-cookie if needed, or simple regex
		const match = document.cookie.match(/idToken=([^;]+)/);
		if (match) token = match[1];
	}

	return yield* call.next(call.request, {
		...options,
		metadata: Metadata(options.metadata).set(
			"Authorization",
			token ? `Bearer ${token}` : "",
		),
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
