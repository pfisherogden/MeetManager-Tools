import { loadDataFromUrl } from '../src/services/dataLoader';
import { setSyncEndpoint, initSyncService, triggerSync } from '../src/services/syncService';
import * as db from '../src/database/db';
import NetInfo from '@react-native-community/netinfo';
import { Linking, Platform } from 'react-native';

// Mock dependencies
jest.mock('@react-native-community/netinfo', () => ({
  fetch: jest.fn(),
  addEventListener: jest.fn(),
}));

// Mock fetch
global.fetch = jest.fn();

// Mock DB
jest.mock('../src/database/db', () => ({
  loadFromJSON: jest.fn(),
  getPendingDQs: jest.fn(() => [{ id: 1, dq_code: '1A' }]),
  markAsSynced: jest.fn(),
}));

describe('Data Loader Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('loads data from initial URL on native', async () => {
    Platform.OS = 'ios';
    // Use type casting to mock the method if necessary, or just assume it's a jest mock
    (Linking.getInitialURL as jest.Mock).mockResolvedValue('meetmanager://app?program_url=http://example.com/program.json&dq_url=http://example.com/dqs.json&sync_url=http://example.com/sync');
    
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ events: [] })
    });

    const result = await loadDataFromUrl();

    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(db.loadFromJSON).toHaveBeenCalled();
    expect(result.loaded).toBe(true);
    expect(result.syncUrl).toBe('http://example.com/sync');
  });
});

describe('Sync Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setSyncEndpoint('http://example.com/sync');
  });

  it('syncs pending items when connected', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue({ isConnected: true });
    (global.fetch as jest.Mock).mockResolvedValue({ ok: true });

    await triggerSync();

    expect(global.fetch).toHaveBeenCalledWith('http://example.com/sync', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify([{ id: 1, dq_code: '1A' }])
    }));
    expect(db.markAsSynced).toHaveBeenCalledWith(1);
  });

  it('skips sync if not connected', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue({ isConnected: false });

    await triggerSync();

    expect(global.fetch).not.toHaveBeenCalled();
  });
});
