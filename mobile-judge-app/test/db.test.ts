import * as db from '../src/database/db';

const mockRunSync = jest.fn((query, eventId, swimmerId, dqCode, leg, notes, syncStatus, timestamp) => ({ lastInsertRowId: 1, changes: 1 }));
const mockGetDb = jest.fn(() => ({
  execSync: jest.fn(),
  runSync: mockRunSync,
  getAllSync: jest.fn(() => []),
  getFirstSync: jest.fn(() => ({ count: 0 })),
}));

jest.mock('../src/database/db', () => ({
  initDatabase: jest.fn(),
  getDb: mockGetDb,
  saveDQ: jest.fn((eventId, swimmerId, dqCode, leg, notes) => {
    mockGetDb().runSync(
      'INSERT INTO dqs (event_id, swimmer_id, dq_code, leg, notes, sync_status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
      eventId,
      swimmerId,
      dqCode,
      leg,
      notes,
      'pending',
      new Date().toISOString()
    );
    return { changes: 1 };
  }),
  getPendingDQs: jest.fn(() => []),
  markAsSynced: jest.fn(),
}));

describe('Database Offline Persistence', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetDb.mockClear();
    mockRunSync.mockClear();
    (db.initDatabase as jest.Mock).mockClear();
    (db.saveDQ as jest.Mock).mockClear();
    db.initDatabase();
  });

  it('should save a DQ locally when offline', () => {
    const eventId = 101;
    const swimmerId = 505;
    const dqCode = '1A';

    const result = db.saveDQ(eventId, swimmerId, dqCode);

    expect(result.changes).toBe(1);
    expect(mockRunSync).toHaveBeenCalledWith(
      expect.stringContaining('INSERT INTO dqs'),
      eventId,
      swimmerId,
      dqCode,
      undefined, // leg
      undefined, // notes
      'pending',
      expect.any(String) // timestamp
    );
  });
});
