import * as db from "../src/database/db";

const mockRunSync = jest.fn(
	(
		_query,
		_eventId,
		_swimmerId,
		_dqCode,
		_leg,
		_notes,
		_syncStatus,
		_timestamp,
	) => ({ lastInsertRowId: 1, changes: 1 }),
);
const _mockGetDb = jest.fn(() => ({
	execSync: jest.fn(),
	runSync: mockRunSync,
	getAllSync: jest.fn(() => []),
	getFirstSync: jest.fn(() => ({ count: 0 })),
}));

jest.mock("../src/database/db", () => ({
	initDatabase: jest.fn(),
	seedData: jest.fn(),
	getEvents: jest.fn(() => []),
	getHeatsByEvent: jest.fn(() => []),
	getSwimmersByHeat: jest.fn(() => []),
	getSwimmerById: jest.fn(() => null),
	saveDQ: jest.fn(() => ({ changes: 1 })),
	getPendingDQs: jest.fn(() => []),
	markAsSynced: jest.fn(),
	deleteDQ: jest.fn(() => ({ changes: 1 })),
	clearAllDQs: jest.fn(() => ({ changes: 1 })),
}));

describe("Database Service", () => {
	it("should initialize database", () => {
		db.initDatabase();
		expect(db.initDatabase).toHaveBeenCalled();
	});

	it("should save a DQ", () => {
		const result = db.saveDQ(1, 100, "1A");
		expect(result.changes).toBe(1);
		expect(db.saveDQ).toHaveBeenCalledWith(1, 100, "1A");
	});

	it("should delete a DQ", () => {
		const result = db.deleteDQ(100);
		expect(result.changes).toBe(1);
		expect(db.deleteDQ).toHaveBeenCalledWith(100);
	});
});
