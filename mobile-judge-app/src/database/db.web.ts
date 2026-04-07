import { Platform } from "react-native";
import type { DQ, Event, Heat, Swimmer } from "../types";
import sampleData from "../../assets/sample_program.json";

// Web Mock State
let mockEvents: Event[] = [];
let mockHeats: Heat[] = [];
let mockSwimmers: Swimmer[] = [];
let mockDQs: DQ[] = [];

export const getDb = () => {
	return {
		execSync: () => { },
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

		if (sampleData && sampleData.events) {
			mockEvents = [...(sampleData.events as unknown as Event[])];
			mockHeats = [...(sampleData.heats as unknown as Heat[])];
			mockSwimmers = [...(sampleData.swimmers as unknown as Swimmer[])];

			// Add a custom Boys relay event for variety (if not already present)
			const hasBoysRelay = mockEvents.some((e) => e.name.includes("Boys") && e.isRelay);
			if (!hasBoysRelay) {
				const nextEventId = Math.max(0, ...mockEvents.map((e) => e.id)) + 1;
				const nextHeatId = Math.max(0, ...mockHeats.map((h) => h.id)) + 1;
				const nextSwimmerId = Math.max(0, ...mockSwimmers.map((s) => s.id)) + 1;

				mockEvents.push({
					id: nextEventId,
					number: 81,
					name: "Boys 8&U 100 Free Relay",
					distance: 100,
					stroke: "Free",
					isRelay: true,
				});

				mockHeats.push({
					id: nextHeatId,
					number: 1,
					event_id: nextEventId,
					swimmers: [],
				});

				mockSwimmers.push({
					id: nextSwimmerId,
					lane: 1, // Diversify!
					name: "Speedy Sharks Team A",
					team: "SHARK",
					heat_id: nextHeatId,
					isRelay: true,
					members: ["Leo D.", "Guy F.", "Tim C.", "Bob J."],
					relay_dqs: [],
					notes: "",
					dq_code: "",
				});
			}

			// Diversify some existing mid-lane assignments to lanes 1 and 6 for testing
			mockSwimmers.slice(0, 10).forEach((s, idx) => {
				if (idx % 3 === 0) s.lane = 1;
				if (idx % 3 === 1) s.lane = 6;
			});

			console.log("Web Mock DB Seeded from comprehensive JSON with enhancements:", {
				events: mockEvents.length,
				heats: mockHeats.length,
				swimmers: mockSwimmers.length,
			});
			return;
		}

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
				name: "Boys 8&U 100 Free Relay",
				distance: 100,
				stroke: "Free",
				isRelay: true,
			},
			{
				id: 3,
				number: 3,
				name: "Girls 9-10 50 Free",
				distance: 50,
				stroke: "Free",
				isRelay: false,
			},
		];

		mockHeats = [
			{ id: 1, number: 1, event_id: 1, swimmers: [] },
			{ id: 2, number: 1, event_id: 2, swimmers: [] },
			{ id: 3, number: 1, event_id: 3, swimmers: [] },
		];

		mockSwimmers = [
			{
				id: 1,
				lane: 1,
				name: "Alice Smith",
				team: "FAST",
				heat_id: 1,
				isRelay: true,
				members: ["Alice S.", "Dana R.", "Zoe M.", "Mia K."],
				relay_dqs: [],
				notes: "",
				dq_code: "",
			},
			{
				id: 2,
				lane: 3,
				name: "Bob Jones",
				team: "FAST",
				heat_id: 2,
				isRelay: true,
				members: ["Bob J.", "Tim C.", "Leo D.", "Guy F."],
				relay_dqs: [],
				notes: "",
				dq_code: "",
			},
			{
				id: 3,
				lane: 5,
				name: "Charlie Brown",
				team: "FAST",
				heat_id: 3,
				isRelay: false,
				members: [],
				relay_dqs: [],
				notes: "",
				dq_code: "",
			},
			{
				id: 4,
				lane: 6,
				name: "David Wilson",
				team: "STORM",
				heat_id: 3,
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

export const getEventById = (id: number): Event | null => {
	return mockEvents.find((e) => e.id === id) || null;
};

export const getHeatById = (id: number): Heat | null => {
	return mockHeats.find((h) => h.id === id) || null;
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

const parseSwimmerId = (id: number | string): number => {
	if (typeof id === "number") return id;
	// Handle strings like "Relay-1" or "empty-101"
	const numeric = id.replace(/[^0-9]/g, "");
	return parseInt(numeric, 10) || 0;
};

export const saveDQ = (
	eventId: number,
	swimmerId: number | string,
	dqCode: string,
	leg?: number,
	notes?: string,
) => {
	const sid = parseSwimmerId(swimmerId);
	console.log("Web Mock DQ Saved:", { eventId, swimmerId, sid, dqCode, leg, notes });

	// Remove existing DQ for the same context
	if (leg) {
		mockDQs = mockDQs.filter(
			(dq) => !(dq.swimmer_id === sid && dq.leg === leg && dq.event_id === eventId),
		);
	} else {
		mockDQs = mockDQs.filter((dq) => !(dq.swimmer_id === sid && !dq.leg && dq.event_id === eventId));
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
	const sid = parseSwimmerId(swimmerId);
	mockDQs = mockDQs.filter((d) => !(d.swimmer_id === sid && d.leg === leg));
	return { changes: 1 };
};

export const clearAllDQs = () => {
	mockDQs = [];
	return { changes: 1 };
};
