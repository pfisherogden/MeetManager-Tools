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
// - Server Side (Docker): use 'backend:50051' (or env var)
// - Client Side (Browser): use 'localhost:50051'
// Note: NEXT_PUBLIC_ variables are for browser, but here we check window context
const defaultHost =
	typeof window === "undefined"
		? process.env.BACKEND_INTERNAL_HOST || "localhost:50051"
		: "localhost:50051";

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

const client: MeetManagerServiceClient = clientFactory.create(
	MeetManagerServiceDefinition,
	createChannel(defaultHost, ChannelCredentials.createInsecure()),
);

export default client;
