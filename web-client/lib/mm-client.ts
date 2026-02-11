import {
	ChannelCredentials,
	createChannel,
	createClientFactory,
} from "nice-grpc";
import {
	type MeetManagerServiceClient,
	MeetManagerServiceDefinition,
} from "./proto/meet_manager";

// Determine host:
// - Server Side (Docker): use 'backend:50051' (or env var)
// - Client Side (Browser): use 'localhost:50051'
// Note: NEXT_PUBLIC_ variables are for browser, but here we check window context
const defaultHost =
	typeof window === "undefined"
		? process.env.BACKEND_INTERNAL_HOST || "localhost:50051"
		: "localhost:50051";

// Create a singleton client
const clientFactory = createClientFactory();

const client: MeetManagerServiceClient = clientFactory.create(
	MeetManagerServiceDefinition,
	createChannel(defaultHost, ChannelCredentials.createInsecure()),
);

export default client;
