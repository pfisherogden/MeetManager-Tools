import NetInfo from "@react-native-community/netinfo";
import {
	getEventById,
	getHeatById,
	getPendingDQs,
	getSwimmerById,
	markAsSynced,
} from "../database/db";

let SYNC_ENDPOINT = "";
let onSyncComplete: (() => void) | null = null;

export const setSyncEndpoint = (url: string) => {
	SYNC_ENDPOINT = url;
};

export const initSyncService = (callback: () => void) => {
	onSyncComplete = callback;

	// Listen for network changes
	NetInfo.addEventListener((state) => {
		if (state.isConnected && SYNC_ENDPOINT) {
			triggerSync();
		}
	});
};

export const triggerSync = async () => {
	if (!SYNC_ENDPOINT) return;

	const pending = getPendingDQs();
	if (pending.length === 0) return;

	const state = await NetInfo.fetch();
	if (!state.isConnected) return;

	// Optimization: If the endpoint is sync-dqs, we should ideally use submit-dq for individual items
	// or wrap the single item in an array. The web-client provides /api/submit-dq for this purpose.
	let targetUrl = SYNC_ENDPOINT;
	if (SYNC_ENDPOINT.includes("/api/sync-dqs")) {
		targetUrl = SYNC_ENDPOINT.replace("/api/sync-dqs", "/api/submit-dq");
	}

	console.log(`Syncing ${pending.length} items to ${targetUrl}`);

	try {
		const method = "POST";
		let allSuccess = true;
		let anySuccess = false;

		for (const item of pending) {
			const swimmer = getSwimmerById(item.swimmer_id);
			if (!swimmer) {
				console.warn(`Swimmer ${item.swimmer_id} not found, skipping sync for DQ ${item.id}`);
				continue;
			}

			const heat = getHeatById(swimmer.heat_id);
			const event = getEventById(item.event_id);

			const timestampMs = new Date(item.timestamp).getTime();
			const clientDqId = `dq-${item.id}-${timestampMs}`;

			// Load judge name for traceability
			const judgeName = (typeof window !== "undefined" && window.localStorage) 
				? window.localStorage.getItem("mmtools_judge_name") || "Unknown"
				: "Unknown";

			// For relays, include the specific member name if a leg was DQ'd
			let swimmerDisplay = swimmer.name;
			if (item.leg && swimmer.members && swimmer.members[item.leg - 1]) {
				const legMember = swimmer.members[item.leg - 1];
				swimmerDisplay = `${swimmer.name} (Leg ${item.leg}: ${legMember})`;
			}

			const payload = {
				clientDqId,
				client_id: judgeName,
				event: event ? event.number : item.event_id,
				heat: heat ? heat.number : swimmer.heat_id,
				lane: swimmer.lane,
				swimmer: swimmerDisplay,
				infraction_code: item.dq_code,
			};

			console.log(`Sending DQ POST to ${targetUrl} for swimmer ${swimmer.name}`);
			try {
				const response = await fetch(targetUrl, {
					method,
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(payload),
				});

				if (response.ok) {
					console.log(`Successfully synced DQ ${item.id}`);
					markAsSynced(item.id);
					anySuccess = true;
				} else {
					const errorText = await response.text();
					console.error(
						"Sync failed for item",
						item.id,
						"Status:", response.status,
						"Error:", errorText,
					);
					allSuccess = false;
				}
			} catch (fetchError: any) {
				console.error(`Fetch error during sync for DQ ${item.id}:`, fetchError.message);
				allSuccess = false;
			}
		}

		if (anySuccess || (pending.length > 0 && allSuccess)) {
			console.log(`Sync iteration complete. Any success: ${anySuccess}`);
			if (onSyncComplete) onSyncComplete();
		}
	} catch (e) {
		console.error("Sync error", e);
	}
};
