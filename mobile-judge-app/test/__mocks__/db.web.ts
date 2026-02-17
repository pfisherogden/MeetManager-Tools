export const getDb = jest.fn(() => ({
  execSync: jest.fn(),
  runSync: jest.fn(() => ({ lastInsertRowId: 1, changes: 1 })),
  getAllSync: jest.fn(() => []),
  getFirstSync: jest.fn(() => ({ count: 0 })),
}));

export const initDatabase = jest.fn();
export const resetDatabase = jest.fn();
export const loadFromJSON = jest.fn();
export const seedData = jest.fn();
export const getEvents = jest.fn(() => []);
export const getHeatsByEvent = jest.fn(() => []);
export const getSwimmersByHeat = jest.fn(() => []);
export const saveDQ = jest.fn(() => ({ changes: 1 }));
export const getPendingDQs = jest.fn(() => []);
export const markAsSynced = jest.fn();
