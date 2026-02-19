import { Platform } from "react-native";
import type { DQ, Event, Heat, Swimmer } from "../types";

let _db: any = null;

export const getDb = () => {
	if (Platform.OS === "web") {
		// Return a mock DB for web review in Docker
		return {
			execSync: () => {},
			runSync: () => ({ lastInsertRowId: 1, changes: 1 }),
			getAllSync: (_query: string) => [],
			getFirstSync: () => ({ count: 0 }),
		};
	}

	// Use require for native only to avoid web bundling issues with WASM
	const SQLite = require("expo-sqlite");
	if (!_db) {
		_db = SQLite.openDatabaseSync("meetmanager_judge.db");
	}
	return _db;
};

export const initDatabase = () => {
	if (Platform.OS === "web") return;
	const db = getDb();
	db.execSync(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY,
      number INTEGER NOT NULL,
      name TEXT NOT NULL,
      distance INTEGER,
      stroke TEXT,
      isRelay INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS heats (
      id INTEGER PRIMARY KEY,
      event_id INTEGER NOT NULL,
      number INTEGER NOT NULL,
      FOREIGN KEY(event_id) REFERENCES events(id)
    );
    CREATE TABLE IF NOT EXISTS swimmers (
      id INTEGER PRIMARY KEY,
      heat_id INTEGER NOT NULL,
      lane INTEGER NOT NULL,
      name TEXT NOT NULL,
      team TEXT NOT NULL,
      members TEXT,
      FOREIGN KEY(heat_id) REFERENCES heats(id)
    );
    CREATE TABLE IF NOT EXISTS dqs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      event_id INTEGER NOT NULL,
      swimmer_id INTEGER NOT NULL,
      leg INTEGER,
      dq_code TEXT NOT NULL,
      notes TEXT,
      sync_status TEXT DEFAULT 'pending',
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(event_id, swimmer_id, leg)
    );
  `);
};

export const resetDatabase = () => {
	if (Platform.OS === "web") return;
	const db = getDb();
	db.execSync("DELETE FROM dqs");
	db.execSync("DELETE FROM swimmers");
	db.execSync("DELETE FROM heats");
	db.execSync("DELETE FROM events");
};

export const loadFromJSON = (programData: {
	events: Event[];
	heats: Heat[];
	swimmers: Swimmer[];
}) => {
	if (Platform.OS === "web") return;

	const db = getDb();
	resetDatabase();

	if (programData.events) {
		for (const evt of programData.events) {
			db.runSync(
				"INSERT INTO events (id, number, name, distance, stroke, isRelay) VALUES (?, ?, ?, ?, ?, ?)",
				evt.id,
				evt.number,
				evt.name,
				evt.distance,
				evt.stroke,
				evt.isRelay ? 1 : 0,
			);
		}
	}

	if (programData.heats) {
		for (const heat of programData.heats) {
			db.runSync(
				"INSERT INTO heats (id, event_id, number) VALUES (?, ?, ?)",
				heat.id,
				heat.event_id,
				heat.number,
			);
		}
	}

	if (programData.swimmers) {
		for (const s of programData.swimmers) {
			db.runSync(
				"INSERT INTO swimmers (id, heat_id, lane, name, team, members) VALUES (?, ?, ?, ?, ?, ?)",
				s.id,
				s.heat_id,
				s.lane,
				s.name,
				s.team,
				s.members ? JSON.stringify(s.members) : null,
			);
		}
	}
};

export const seedData = () => {
	if (Platform.OS === "web") return;
	const db = getDb();
	const eventCount = db.getFirstSync(
		"SELECT COUNT(*) as count FROM events",
	) as { count: number };
	if (eventCount.count > 0) return;

	db.execSync(`
    INSERT INTO events (id, number, name, distance, stroke, isRelay) VALUES (1, 1, 'Girls 8&U 100 Medley Relay', 100, 'Medley', 1);
    INSERT INTO events (id, number, name, distance, stroke, isRelay) VALUES (2, 2, 'Boys 8&U 100 Medley Relay', 100, 'Medley', 1);
    INSERT INTO events (id, number, name, distance, stroke, isRelay) VALUES (3, 3, 'Girls 9-10 200 Medley Relay', 200, 'Medley', 1);

    INSERT INTO heats (id, event_id, number) VALUES (1, 1, 1);
    INSERT INTO heats (id, event_id, number) VALUES (2, 1, 2);

    INSERT INTO swimmers (id, heat_id, lane, name, team) VALUES (1, 1, 1, 'Alice Smith', 'FAST');
    INSERT INTO swimmers (id, heat_id, lane, name, team) VALUES (2, 1, 2, 'Bob Jones', 'FAST');
    INSERT INTO swimmers (id, heat_id, lane, name, team) VALUES (3, 1, 3, 'Charlie Brown', 'SLOW');
    INSERT INTO swimmers (id, heat_id, lane, name, team) VALUES (4, 1, 4, 'Daisy Miller', 'SLOW');
  `);
};

export const getEvents = (): Event[] => {
	if (Platform.OS === "web") return [];
	const rows = getDb().getAllSync("SELECT * FROM events ORDER BY number ASC");
	return rows.map((r: any) => ({ ...r, isRelay: !!r.isRelay }));
};

export const getHeatsByEvent = (eventId: number): Heat[] => {
	if (Platform.OS === "web") return [];
	return getDb().getAllSync(
		"SELECT * FROM heats WHERE event_id = ? ORDER BY number ASC",
		eventId,
	);
};

export const getSwimmersByHeat = (heatId: number): Swimmer[] => {
	if (Platform.OS === "web") return [];
	const db = getDb();
	const rows = db.getAllSync(
		`
    SELECT s.*, d.dq_code, d.notes, d.leg, e.isRelay as eventIsRelay
    FROM swimmers s
    JOIN heats h ON s.heat_id = h.id
    JOIN events e ON h.event_id = e.id
    LEFT JOIN dqs d ON s.id = d.swimmer_id AND d.event_id = h.event_id
    WHERE s.heat_id = ? 
    ORDER BY s.lane ASC
  `,
		heatId,
	);

	return rows.map((r: any) => {
		const s: Swimmer = {
			id: r.id,
			heat_id: r.heat_id,
			lane: r.lane,
			name: r.name,
			team: r.team,
			isRelay: !!r.eventIsRelay,
			members: r.members ? JSON.parse(r.members) : [],
			dq_code: r.dq_code,
			notes: r.notes,
			empty: false,
		};

		// Relay DQs are handled slightly differently in the UI via relay_dqs array
		if (s.isRelay) {
			const relayDQs = db.getAllSync(
				"SELECT * FROM dqs WHERE swimmer_id = ? AND event_id = (SELECT event_id FROM heats WHERE id = ?)",
				s.id,
				heatId,
			);
			s.relay_dqs = relayDQs.map((d: any) => ({
				id: d.id,
				event_id: d.event_id,
				swimmer_id: d.swimmer_id,
				dq_code: d.dq_code,
				leg: d.leg,
				notes: d.notes,
				sync_status: d.sync_status,
				timestamp: d.timestamp,
			}));
		}

		return s;
	});
};

export const getSwimmerById = (id: number | string): Swimmer | null => {
	if (Platform.OS === "web") return null;
	const r = getDb().getFirstSync("SELECT * FROM swimmers WHERE id = ?", id);
	if (!r) return null;
	return {
		id: r.id,
		heat_id: r.heat_id,
		lane: r.lane,
		name: r.name,
		team: r.team,
		isRelay: false, // Need more info to be accurate here, but helper usually for individual
		members: r.members ? JSON.parse(r.members) : [],
		empty: false,
	};
};

export const saveDQ = (
	eventId: number,
	swimmerId: number,
	dqCode: string,
	leg?: number,
	notes?: string,
) => {
	if (Platform.OS === "web") {
		console.log("Web Mock DQ Saved:", {
			eventId,
			swimmerId,
			dqCode,
			leg,
			notes,
		});
		return { changes: 1 };
	}
	return getDb().runSync(
		"INSERT OR REPLACE INTO dqs (event_id, swimmer_id, dq_code, leg, notes, sync_status) VALUES (?, ?, ?, ?, ?, ?)",
		eventId,
		swimmerId,
		dqCode,
		leg || null,
		notes || "",
		"pending",
	);
};

export const getPendingDQs = (): DQ[] => {
	if (Platform.OS === "web") return [];
	const rows = getDb().getAllSync(
		"SELECT * FROM dqs WHERE sync_status = ?",
		"pending",
	);
	return rows.map((r: any) => ({
		id: r.id,
		event_id: r.event_id,
		swimmer_id: r.swimmer_id,
		dq_code: r.dq_code,
		leg: r.leg,
		notes: r.notes,
		sync_status: r.sync_status,
		timestamp: r.timestamp,
	}));
};

export const markAsSynced = (id: number) => {
	if (Platform.OS === "web") return;
	return getDb().runSync(
		"UPDATE dqs SET sync_status = ? WHERE id = ?",
		"synced",
		id,
	);
};

export const deleteDQ = (swimmerId: number | string, leg?: number) => {
	if (Platform.OS === "web") return;
	return getDb().runSync(
		"DELETE FROM dqs WHERE swimmer_id = ? AND (leg = ? OR (leg IS NULL AND ? IS NULL))",
		swimmerId,
		leg || null,
		leg || null,
	);
};

export const clearAllDQs = () => {
	if (Platform.OS === "web") return;
	return getDb().runSync("DELETE FROM dqs WHERE sync_status = ?", "pending");
};
