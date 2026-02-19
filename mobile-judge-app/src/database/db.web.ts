import { Platform } from "react-native";
import type { DQ, Event, Heat, Swimmer } from "../types";

// Web Mock State
let mockEvents: Event[] = [];
let mockHeats: Heat[] = [];
let mockSwimmers: Swimmer[] = [];
let mockDQs: DQ[] = [];

export const getDb = () => {
	return {
		execSync: () => {},
		runSync: () => ({ lastInsertRowId: 1, changes: 1 }),
		getAllSync: (_query: string) => [],
		getFirstSync: () => ({ count: 0 }),
	};
};

export const initDatabase = () => {
	if (Platform.OS === "web") {
		// Reset or ensure initial state
		if (mockEvents.length === 0) {
			// Default mock data if nothing loaded
		}
	}
};

export const resetDatabase = () => {
	mockEvents = [];
	mockHeats = [];
	mockSwimmers = [];
	mockDQs = [];
};

export const loadFromJSON = (programData: {
	events: Event[];
	heats: Heat[];
	swimmers: Swimmer[];
}) => {
	if (Platform.OS === "web") {
		resetDatabase();
		if (programData.events) mockEvents = programData.events;
		if (programData.heats) mockHeats = programData.heats;
		if (programData.swimmers) mockSwimmers = programData.swimmers;
		console.log("Web Mock DB Loaded from JSON:", {
			events: mockEvents.length,
			heats: mockHeats.length,
			swimmers: mockSwimmers.length,
		});
	}
};

export const seedData = () => {
	if (Platform.OS === "web") {
		if (mockEvents.length > 0) return; // Already seeded or loaded

		mockEvents = [
			{
				id: 1,
				number: 1,
				name: "Girls 8&U 100 Medley Relay",
				distance: 100,
				stroke: "Medley",
				isRelay: true,
			},
			{
				id: 2,
				number: 2,
				name: "Boys 8&U 100 Medley Relay",
				distance: 100,
				stroke: "Medley",
				isRelay: true,
			},
		];

		mockHeats = [{ id: 1, number: 1, event_id: 1, swimmers: [] }];

		mockSwimmers = [
			{
				id: 1,
				lane: 1,
				name: "Alice Smith",
				team: "FAST",
				heat_id: 1,
				isRelay: false,
				members: [],
				relay_dqs: [],
				notes: "",
				dq_code: "",
			},
			{
				id: 2,
				lane: 2,
				name: "Bob Jones",
				team: "FAST",
				heat_id: 1,
				isRelay: false,
				members: [],
				relay_dqs: [],
				notes: "",
				dq_code: "",
			},
		];
	}
};

export const getEvents = (): Event[] => {
	return [...mockEvents].sort((a, b) => a.number - b.number);
};

export const getHeatsByEvent = (eventId: number): Heat[] => {
	return mockHeats
		.filter((h) => h.event_id === eventId)
		.sort((a, b) => a.number - b.number);
};

export const getSwimmersByHeat = (heatId: number): Swimmer[] => {
	const heat = mockHeats.find((h) => h.id === heatId);
	const event = heat ? mockEvents.find((e) => e.id === heat.event_id) : null;
	const isRelay = event ? event.isRelay : false;

	const swimmers = mockSwimmers
		.filter((s) => s.heat_id === heatId)
		.sort((a, b) => a.lane - b.lane);

	// Create a map for quick lookup
	const swimmerMap = new Map(swimmers.map((s) => [s.lane, s]));

	const result: Swimmer[] = [];
	// Assume 6 lanes for now
	for (let lane = 1; lane <= 6; lane++) {
		if (swimmerMap.has(lane)) {
			const s = swimmerMap.get(lane)!;

			const relayDQs = mockDQs.filter((dq) => dq.swimmer_id === s.id && dq.leg);
			const individualDQ = mockDQs.find(
				(dq) => dq.swimmer_id === s.id && !dq.leg,
			);

			result.push({
				...s,
				dq_code: individualDQ?.dq_code || "",
				notes: individualDQ?.notes || "",
				relay_dqs: isRelay ? relayDQs : [],
				isRelay: isRelay,
				empty: false,
			});
		} else {
			const emptyId = 10000 + heatId * 10 + lane; // Synthetic numeric ID
			const individualDQ = mockDQs.find((dq) => dq.swimmer_id === emptyId);

			result.push({
				id: emptyId,
				lane: lane,
				name: "Empty",
				team: "",
				heat_id: heatId,
				isRelay: isRelay,
				members: [],
				relay_dqs: [],
				dq_code: individualDQ?.dq_code || "",
				notes: individualDQ?.notes || "",
				empty: true,
			});
		}
	}
	return result;
};

export const getSwimmerById = (id: number | string): Swimmer | null => {
	const s = mockSwimmers.find((sw) => sw.id === id);
	if (s) {
		const heat = mockHeats.find((h) => h.id === s.heat_id);
		const event = heat ? mockEvents.find((e) => e.id === heat.event_id) : null;
		return {
			...s,
			isRelay: event ? event.isRelay : false,
			empty: false,
		};
	}
	return null;
};

export const saveDQ = (
	eventId: number,
	swimmerId: number | string,
	dqCode: string,
	leg?: number,
	notes?: string,
) => {
	console.log("Web Mock DQ Saved:", { eventId, swimmerId, dqCode, leg, notes });

	const sid =
		typeof swimmerId === "string"
			? parseInt(swimmerId.replace("empty-", ""), 10)
			: swimmerId;

	// Remove existing DQ for the same context
	if (leg) {
		mockDQs = mockDQs.filter(
			(dq) => !(dq.swimmer_id === sid && dq.leg === leg),
		);
	} else {
		mockDQs = mockDQs.filter((dq) => !(dq.swimmer_id === sid && !dq.leg));
	}

	const newDQ: DQ = {
		id: mockDQs.length + 1,
		event_id: eventId,
		swimmer_id: sid,
		dq_code: dqCode,
		leg,
		notes: notes || "",
		sync_status: "pending",
		timestamp: new Date().toISOString(),
	};

	mockDQs.push(newDQ);
	return { changes: 1 };
};

export const getPendingDQs = (): DQ[] => {
	return mockDQs.filter((dq) => dq.sync_status === "pending");
};

export const markAsSynced = (id: number) => {
	const dq = mockDQs.find((d) => d.id === id);
	if (dq) {
		dq.sync_status = "synced";
	}
};

export const deleteDQ = (swimmerId: number | string, leg?: number) => {
	const sid =
		typeof swimmerId === "string"
			? parseInt(swimmerId.replace("empty-", ""), 10)
			: swimmerId;
	mockDQs = mockDQs.filter((d) => !(d.swimmer_id === sid && d.leg === leg));
	return { changes: 1 };
};

export const clearAllDQs = () => {
	mockDQs = [];
	return { changes: 1 };
};
