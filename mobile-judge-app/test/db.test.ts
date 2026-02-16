import { saveDQ, initDatabase, getDb } from '../src/database/db';
import * as SQLite from 'expo-sqlite';

describe('Database Offline Persistence', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    initDatabase();
  });

  it('should save a DQ locally when offline', () => {
    const eventId = 101;
    const swimmerId = 505;
    const dqCode = '1A';

    const result = saveDQ(eventId, swimmerId, dqCode);
    const db = getDb();

    expect(result.changes).toBe(1);
    expect(db.runSync).toHaveBeenCalledWith(
      expect.stringContaining('INSERT INTO dqs'),
      eventId,
      swimmerId,
      dqCode,
      'pending'
    );
  });
});
