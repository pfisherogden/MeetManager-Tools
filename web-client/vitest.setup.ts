import { vi } from "vitest";

// Globally mock fetch to prevent live network requests in unit tests
global.fetch = vi.fn(() =>
	Promise.reject(new Error("Network request blocked in unit tests")),
);

const mockActions = {
	listDatasets: vi.fn(() => Promise.resolve({ datasets: [] })),
	setActiveDataset: vi.fn(() => Promise.resolve({ success: true })),
	deleteDataset: vi.fn(() => Promise.resolve({ success: true })),
	clearAllDatasets: vi.fn(() => Promise.resolve({ success: true })),
	uploadDataset: vi.fn(() => Promise.resolve({ success: true })),
	uploadDatasetFromDrive: vi.fn(() => Promise.resolve({ success: true })),
	publishMeetData: vi.fn(() => Promise.resolve({ success: true })),
	validateActiveMeet: vi.fn(() =>
		Promise.resolve({ success: true, findings: [] }),
	),
	getMeets: vi.fn(() => Promise.resolve({ meets: [] })),
	getTeams: vi.fn(() => Promise.resolve({ teams: [] })),
	getAthletes: vi.fn(() => Promise.resolve({ athletes: [] })),
	getEntries: vi.fn(() => Promise.resolve({ entries: [] })),
	getSessions: vi.fn(() => Promise.resolve({ sessions: [] })),
	getRelays: vi.fn(() => Promise.resolve({ relays: [] })),
	getScores: vi.fn(() => Promise.resolve({ scores: [] })),
	getEventScores: vi.fn(() => Promise.resolve({ eventScores: [] })),
	getEvents: vi.fn(() => Promise.resolve({ events: [] })),
	getAdminConfig: vi.fn(() =>
		Promise.resolve({ meetName: "Test Meet", meetDescription: "" }),
	),
	getGoogleConfig: vi.fn(() =>
		Promise.resolve({ apiKey: "", clientId: "", appId: "" }),
	),
	getDisqualifications: vi.fn(() => Promise.resolve({ disqualifications: [] })),
	deleteDq: vi.fn(() => Promise.resolve({ success: true })),
	clearAllDqs: vi.fn(() => Promise.resolve({ success: true })),
	generateReportBundle: vi.fn(() =>
		Promise.resolve({ success: true, jobId: "123" }),
	),
	getJobStatus: vi.fn(() =>
		Promise.resolve({ status: "COMPLETED", progress: 100 }),
	),
	getDashboardStats: vi.fn(() =>
		Promise.resolve({
			meetCount: 0,
			teamCount: 0,
			athleteCount: 0,
			eventCount: 0,
		}),
	),
};

// Mock both routes to cover Next.js bundle resolution under Vitest
vi.mock("@/app/actions", () => mockActions);
vi.mock("@/app/actions.client", () => mockActions);
vi.mock("../app/actions", () => mockActions);
vi.mock("../app/actions.client", () => mockActions);
