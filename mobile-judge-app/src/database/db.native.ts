import { Platform } from 'react-native';

let _db: any = null;

export const getDb = () => {
  if (Platform.OS === 'web') {
    // Return a mock DB for web review in Docker
    return {
      execSync: () => {},
      runSync: () => ({ lastInsertRowId: 1, changes: 1 }),
      getAllSync: (query: string) => [],
      getFirstSync: () => ({ count: 0 }),
    };
  }
  
  // Use require for native only to avoid web bundling issues with WASM
  const SQLite = require('expo-sqlite');
  if (!_db) {
    _db = SQLite.openDatabaseSync('meetmanager_judge.db');
  }
  return _db;
};

export const initDatabase = () => {
  if (Platform.OS === 'web') return;
  const db = getDb();
  db.execSync(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY,
      number INTEGER NOT NULL,
      name TEXT NOT NULL,
      distance INTEGER,
      stroke TEXT
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
      FOREIGN KEY(heat_id) REFERENCES heats(id)
    );
    CREATE TABLE IF NOT EXISTS dqs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      event_id INTEGER NOT NULL,
      swimmer_id INTEGER NOT NULL,
      dq_code TEXT NOT NULL,
      sync_status TEXT DEFAULT 'pending',
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
  `);
};

export const seedData = () => {
  if (Platform.OS === 'web') return;
  const db = getDb();
  const eventCount = db.getFirstSync('SELECT COUNT(*) as count FROM events') as { count: number };
  if (eventCount.count > 0) return;

  db.execSync(`
    INSERT INTO events (id, number, name, distance, stroke) VALUES (1, 1, 'Girls 8&U 100 Medley Relay', 100, 'Medley');
    INSERT INTO events (id, number, name, distance, stroke) VALUES (2, 2, 'Boys 8&U 100 Medley Relay', 100, 'Medley');
    INSERT INTO events (id, number, name, distance, stroke) VALUES (3, 3, 'Girls 9-10 200 Medley Relay', 200, 'Medley');

    INSERT INTO heats (id, event_id, number) VALUES (1, 1, 1);
    INSERT INTO heats (id, event_id, number) VALUES (2, 1, 2);

    INSERT INTO swimmers (id, heat_id, lane, name, team) VALUES (1, 1, 1, 'Alice Smith', 'FAST');
    INSERT INTO swimmers (id, heat_id, lane, name, team) VALUES (2, 1, 2, 'Bob Jones', 'FAST');
    INSERT INTO swimmers (id, heat_id, lane, name, team) VALUES (3, 1, 3, 'Charlie Brown', 'SLOW');
    INSERT INTO swimmers (id, heat_id, lane, name, team) VALUES (4, 1, 4, 'Daisy Miller', 'SLOW');
  `);
};

export const getEvents = () => {
  if (Platform.OS === 'web') {
    return [
      { id: 1, number: 1, name: 'Girls 8&U 100 Medley Relay' },
      { id: 2, number: 2, name: 'Boys 8&U 100 Medley Relay' }
    ];
  }
  return getDb().getAllSync('SELECT * FROM events ORDER BY number ASC');
};

export const getHeatsByEvent = (eventId: number) => {
  if (Platform.OS === 'web') {
    return [{ id: 1, number: 1, event_id: eventId }];
  }
  return getDb().getAllSync('SELECT * FROM heats WHERE event_id = ? ORDER BY number ASC', eventId);
};

export const getSwimmersByHeat = (heatId: number) => {
  if (Platform.OS === 'web') {
    return [
      { id: 1, lane: 1, name: 'Alice Smith', team: 'FAST' },
      { id: 2, lane: 2, name: 'Bob Jones', team: 'FAST' }
    ];
  }
  return getDb().getAllSync('SELECT * FROM swimmers WHERE heat_id = ? ORDER BY lane ASC', heatId);
};

export const saveDQ = (eventId: number, swimmerId: number, dqCode: string) => {
  if (Platform.OS === 'web') {
    console.log('Web Mock DQ Saved:', { eventId, swimmerId, dqCode });
    return { changes: 1 };
  }
  return getDb().runSync(
    'INSERT INTO dqs (event_id, swimmer_id, dq_code, sync_status) VALUES (?, ?, ?, ?)',
    eventId,
    swimmerId,
    dqCode,
    'pending'
  );
};

export const getPendingDQs = () => {
  if (Platform.OS === 'web') return [];
  return getDb().getAllSync('SELECT * FROM dqs WHERE sync_status = ?', 'pending');
};

export const markAsSynced = (id: number) => {
  if (Platform.OS === 'web') return;
  return getDb().runSync('UPDATE dqs SET sync_status = ? WHERE id = ?', 'synced', id);
};
