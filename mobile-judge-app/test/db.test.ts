import * as db from '../src/database/db';
import * as SQLite from 'expo-sqlite';

describe('Database Offline Persistence', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    db.initDatabase();
  });

  it('should save a DQ locally when offline', () => {
    const eventId = 101;
    const swimmerId = 505;
    const dqCode = '1A';

    const mockDb = db.getDb();
    const runSyncSpy = jest.spyOn(mockDb, 'runSync');

    const result = db.saveDQ(eventId, swimmerId, dqCode);

    expect(result.changes).toBe(1);
    expect(runSyncSpy).toHaveBeenCalledWith(
      expect.stringContaining('INSERT OR REPLACE INTO dqs'),
      eventId,
      swimmerId,
      dqCode,
      null,
      '',
      'pending'
    );
  });
});
