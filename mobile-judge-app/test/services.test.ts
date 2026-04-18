import NetInfo from "@react-native-community/netinfo";
import { Linking, Platform } from "react-native";
import * as db from "../src/database/db";
import { loadDataFromUrl } from "../src/services/dataLoader";
import { setSyncEndpoint, triggerSync } from "../src/services/syncService";

// Mock dependencies
jest.mock("@react-native-community/netinfo", () => ({
	fetch: jest.fn(),
	addEventListener: jest.fn(),
}));

// Mock fetch
global.fetch = jest.fn();

// Mock DB
jest.mock("../src/database/db", () => ({
	loadFromJSON: jest.fn(),
	getPendingDQs: jest.fn(() => [
		{
			id: 1,
			event_id: 1,
			swimmer_id: 1,
			dq_code: "1A",
			timestamp: "2023-01-01T00:00:00Z",
		},
	]),
	markAsSynced: jest.fn(),
	getSwimmerById: jest.fn(() => ({
		id: 1,
		heat_id: 1,
		lane: 1,
		name: "Test Swimmer",
	})),
	getEventById: jest.fn(() => ({ id: 1, number: 1 })),
	getHeatById: jest.fn(() => ({ id: 1, number: 1 })),
}));

describe("Data Loader Service", () => {
	beforeEach(() => {
		jest.clearAllMocks();
	});

	it("loads data from initial URL on native", async () => {
		Platform.OS = "ios";
		// Use type casting to mock the method if necessary, or just assume it's a jest mock
		(Linking.getInitialURL as jest.Mock).mockResolvedValue(
			"meetmanager://app?program_url=http://example.com/program.json&dq_url=http://example.com/dqs.json&sync_url=http://example.com/sync",
		);

		(global.fetch as jest.Mock).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ events: [] }),
		});

		const result = await loadDataFromUrl();

		expect(global.fetch).toHaveBeenCalledTimes(2);
		expect(db.loadFromJSON).toHaveBeenCalled();
		expect(result.loaded).toBe(true);
		expect(result.syncUrl).toBe("http://example.com/sync");
	});

	it("blocks untrusted URLs", async () => {
		Platform.OS = "ios";
		(Linking.getInitialURL as jest.Mock).mockResolvedValue(
			"meetmanager://app?program_url=http://malicious.com/program.json",
		);

		const result = await loadDataFromUrl();

		expect(global.fetch).not.toHaveBeenCalled();
		expect(result.loaded).toBe(false);
	});

	it("validates program data structure", async () => {
		Platform.OS = "ios";
		(Linking.getInitialURL as jest.Mock).mockResolvedValue(
			"meetmanager://app?program_url=http://example.com/program.json",
		);

		(global.fetch as jest.Mock).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ wrong_key: [] }),
		});

		const result = await loadDataFromUrl();

		expect(global.fetch).toHaveBeenCalled();
		expect(db.loadFromJSON).not.toHaveBeenCalled();
		expect(result.loaded).toBe(false);
	});

	it("validates DQ data structure", async () => {
		Platform.OS = "ios";
		(Linking.getInitialURL as jest.Mock).mockResolvedValue(
			"meetmanager://app?dq_url=http://example.com/dqs.json",
		);

		(global.fetch as jest.Mock).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(["array_not_object"]),
		});

		const result = await loadDataFromUrl();

		expect(global.fetch).toHaveBeenCalled();
		expect(result.dqData).toBeNull();
	});
});

describe("Sync Service", () => {
	beforeEach(() => {
		jest.clearAllMocks();
		setSyncEndpoint("http://example.com/sync");
	});

	it("syncs pending items when connected", async () => {
		(NetInfo.fetch as jest.Mock).mockResolvedValue({ isConnected: true });
		(global.fetch as jest.Mock).mockResolvedValue({ ok: true });

		await triggerSync();

		expect(global.fetch).toHaveBeenCalledWith(
			"http://example.com/sync",
			expect.objectContaining({
				method: "POST",
				body: JSON.stringify({
					clientDqId: "dq-1-1-0",
					client_id: "Unknown",
					event: 1,
					heat: 1,
					lane: 1,
					swimmer: "Test Swimmer",
					infraction_code: "1A",
				}),
			}),
		);
		expect(db.markAsSynced).toHaveBeenCalledWith(1);
	});

	it("skips sync if not connected", async () => {
		(NetInfo.fetch as jest.Mock).mockResolvedValue({ isConnected: false });

		await triggerSync();

		expect(global.fetch).not.toHaveBeenCalled();
	});
});
