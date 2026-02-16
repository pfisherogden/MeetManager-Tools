import NetInfo from '@react-native-community/netinfo';
import { getPendingDQs, markAsSynced } from '../database/db';

let SYNC_ENDPOINT = '';
let onSyncComplete: (() => void) | null = null;

export const setSyncEndpoint = (url: string) => {
  SYNC_ENDPOINT = url;
};

export const initSyncService = (callback: () => void) => {
  onSyncComplete = callback;
  
  // Listen for network changes
  NetInfo.addEventListener(state => {
    if (state.isConnected && SYNC_ENDPOINT) {
      triggerSync();
    }
  });
};

export const triggerSync = async () => {
  if (!SYNC_ENDPOINT) return;
  
  const pending = getPendingDQs();
  if (pending.length === 0) return;

  const state = await NetInfo.fetch();
  if (!state.isConnected) return;

  console.log(`Syncing ${pending.length} items to ${SYNC_ENDPOINT}`);

  try {
    const method = SYNC_ENDPOINT.includes('googleapis') || SYNC_ENDPOINT.includes('amazonaws') ? 'PUT' : 'POST';
    
    const response = await fetch(SYNC_ENDPOINT, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pending)
    });

    if (response.ok) {
      console.log('Sync successful');
      for (const item of pending) {
        markAsSynced(item.id);
      }
      if (onSyncComplete) onSyncComplete();
    } else {
      console.error('Sync failed', response.statusText);
    }
  } catch (e) {
    console.error('Sync error', e);
  }
};
