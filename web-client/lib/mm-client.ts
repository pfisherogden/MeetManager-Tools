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

// Default fallback host:
let defaultHost = "backend:8080";

if (typeof window === "undefined") {
	defaultHost =
		process.env.BACKEND_URL ||
		process.env.BACKEND_INTERNAL_HOST ||
		"backend:8080";
} else {
	const port = process.env.NEXT_PUBLIC_BACKEND_PORT || "8081";
	defaultHost = `localhost:${port}`;
}

const authMiddleware = async function* (call: any, options: any) {
	let token: string | undefined;
	let userId: string | undefined;

	if (typeof window === "undefined") {
		try {
			const { cookies } = await import("next/headers");
			const cookieStore = await cookies();
			token = cookieStore.get("idToken")?.value;
			userId = cookieStore.get("x-user-id")?.value;
		} catch (e) {
			console.warn("Could not retrieve cookies on server", e);
		}
	} else {
		const idTokenMatch = document.cookie.match(/idToken=([^;]+)/);
		if (idTokenMatch) token = idTokenMatch[1];

		const userIdMatch = document.cookie.match(/x-user-id=([^;]+)/);
		if (userIdMatch) userId = userIdMatch[1];
	}

	let metadata = Metadata(options.metadata);
	if (token) metadata = metadata.set("Authorization", `Bearer ${token}`);
	if (userId) metadata = metadata.set("x-user-id", userId);

	if (!token && process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true") {
		metadata = metadata.set("Authorization", "Bearer dev-token");
	}

	return yield* call.next(call.request, {
		...options,
		metadata,
	});
};

const clientFactory = createClientFactory().use(authMiddleware);

let cachedClient: MeetManagerServiceClient | null = null;
let _resolvedHost: string = defaultHost;

async function getOrInitClient(): Promise<MeetManagerServiceClient> {
	if (cachedClient) return cachedClient;

	let targetHost = defaultHost;

	if (typeof window !== "undefined") {
		// Dynamic discovery inside Tauri
		if ((window as any).__TAURI_INTERNALS__) {
			try {
				const { invoke } = await import("@tauri-apps/api/core");
				// Ask Rust for the active sidecar gRPC port
				const ports = await invoke<[number, number]>("get_backend_ports");
				if (ports?.[0]) {
					const dynamicPort = ports[0];
					targetHost = `localhost:${dynamicPort}`;
					console.log(
						`Tauri dynamic discovery: resolved backend port to ${dynamicPort}`,
					);
				}
			} catch (e) {
				console.error("Tauri service discovery failed, using fallback:", e);
			}
		}
	}

	const hostClean = targetHost.replace(/^https?:\/\//, "");
	const useSsl =
		hostClean.includes(".run.app") || process.env.BACKEND_USE_SSL === "true";
	const credentials = useSsl
		? ChannelCredentials.createSsl()
		: ChannelCredentials.createInsecure();

	cachedClient = clientFactory.create(
		MeetManagerServiceDefinition,
		createChannel(hostClean, credentials, {
			"grpc.max_receive_message_length": 50 * 1024 * 1024,
			"grpc.max_send_message_length": 50 * 1024 * 1024,
		}),
	);
	_resolvedHost = hostClean;
	return cachedClient;
}

// Proxy wrapper to support lazy resolution of gRPC endpoints
const clientProxy = new Proxy({} as MeetManagerServiceClient, {
	get(_target, prop, _receiver) {
		if (prop === "then" || prop === "catch" || prop === "constructor") {
			return undefined;
		}
		return async (...args: any[]) => {
			const underlyingClient = await getOrInitClient();
			const fn = (underlyingClient as any)[prop];
			if (typeof fn === "function") {
				return fn.apply(underlyingClient, args);
			}
			return fn;
		};
	},
});

export default clientProxy;
