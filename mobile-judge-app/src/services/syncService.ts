import NetInfo from "@react-native-community/netinfo";
import {
	getPendingDQs,
	markAsSynced,
	getSwimmerById,
	getEventById,
	getHeatById,
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

	console.log(`Syncing ${pending.length} items to ${SYNC_ENDPOINT}`);

	try {
		const method =
			SYNC_ENDPOINT.includes("googleapis") ||
			SYNC_ENDPOINT.includes("amazonaws")
				? "PUT"
				: "POST";

		let allSuccess = true;

		for (const item of pending) {
			const swimmer = getSwimmerById(item.swimmer_id);
			if (!swimmer) continue;

			const heat = getHeatById(swimmer.heat_id);
			const event = getEventById(item.event_id);

			const timestampMs = new Date(item.timestamp).getTime();
			const clientDqId = `dq-${item.id}-${timestampMs}`;

			const payload = {
				clientDqId,
				event: event ? event.number : item.event_id,
				heat: heat ? heat.number : swimmer.heat_id,
				lane: swimmer.lane,
				swimmer: swimmer.name,
				infraction_code: item.dq_code,
			};

			const response = await fetch(SYNC_ENDPOINT, {
				method,
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload),
			});

			if (response.ok) {
				markAsSynced(item.id);
			} else {
				console.error("Sync failed for item", item.id, response.statusText);
				allSuccess = false;
			}
		}

		if (allSuccess) {
			console.log("Sync successful");
			if (onSyncComplete) onSyncComplete();
		}
	} catch (e) {
		console.error("Sync error", e);
	}
};
