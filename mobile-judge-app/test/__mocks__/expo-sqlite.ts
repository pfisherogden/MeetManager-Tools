export const openDatabaseSync = jest.fn(() => ({
  execSync: jest.fn(),
  runSync: jest.fn((query, ...params) => ({ lastInsertRowId: 1, changes: 1 })),
  getAllSync: jest.fn(() => []),
  closeSync: jest.fn(),
}));
