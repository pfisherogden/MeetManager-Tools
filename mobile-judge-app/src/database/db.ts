import { Platform } from 'react-native';

// Web Mock State
let mockEvents: any[] = [];
let mockHeats: any[] = [];
let mockSwimmers: any[] = [];
let mockDQs: any[] = [];

export const getDb = () => {
  return {
    execSync: () => {},
    runSync: () => ({ lastInsertRowId: 1, changes: 1 }),
    getAllSync: (query: string) => [],
    getFirstSync: () => ({ count: 0 }),
  };
};

export const initDatabase = () => {
  if (Platform.OS === 'web') {
    // Reset or ensure initial state
    if (mockEvents.length === 0) {
      // Default mock data if nothing loaded
      // We can leave it empty or seed default if no URL params
    }
  }
};

export const resetDatabase = () => {
  mockEvents = [];
  mockHeats = [];
  mockSwimmers = [];
  mockDQs = [];
};

export const loadFromJSON = (programData: any) => {
  if (Platform.OS === 'web') {
    resetDatabase();
    if (programData.events) mockEvents = programData.events;
    if (programData.heats) mockHeats = programData.heats;
    if (programData.swimmers) mockSwimmers = programData.swimmers;
    console.log('Web Mock DB Loaded from JSON:', { 
      events: mockEvents.length, 
      heats: mockHeats.length, 
      swimmers: mockSwimmers.length 
    });
  } else {
    // Native implementation to bulk insert
    // TODO: Implement bulk insert for native
  }
};

export const seedData = () => {
  if (Platform.OS === 'web') {
    if (mockEvents.length > 0) return; // Already seeded or loaded
    
    mockEvents = [
      { id: 1, number: 1, name: 'Girls 8&U 100 Medley Relay', distance: 100, stroke: 'Medley' },
      { id: 2, number: 2, name: 'Boys 8&U 100 Medley Relay', distance: 100, stroke: 'Medley' }
    ];
    
    mockHeats = [
      { id: 1, number: 1, event_id: 1 }
    ];

    mockSwimmers = [
      { id: 1, lane: 1, name: 'Alice Smith', team: 'FAST', heat_id: 1 },
      { id: 2, lane: 2, name: 'Bob Jones', team: 'FAST', heat_id: 1 }
    ];
  }
};

export const getEvents = () => {
  return mockEvents.sort((a, b) => a.number - b.number);
};

export const getHeatsByEvent = (eventId: number) => {
  return mockHeats
    .filter(h => h.event_id === eventId)
    .sort((a, b) => a.number - b.number);
};

export const getSwimmersByHeat = (heatId: number) => {
  return mockSwimmers
    .filter(s => s.heat_id === heatId)
    .sort((a, b) => a.lane - b.lane);
};

export const saveDQ = (eventId: number, swimmerId: number, dqCode: string) => {
  console.log('Web Mock DQ Saved:', { eventId, swimmerId, dqCode });
  const newDQ = {
    id: mockDQs.length + 1,
    event_id: eventId,
    swimmer_id: swimmerId,
    dq_code: dqCode,
    sync_status: 'pending',
    timestamp: new Date().toISOString()
  };
  mockDQs.push(newDQ);
  return { changes: 1 };
};

export const getPendingDQs = () => {
  return mockDQs.filter(dq => dq.sync_status === 'pending');
};

export const markAsSynced = (id: number) => {
  const dq = mockDQs.find(d => d.id === id);
  if (dq) {
    dq.sync_status = 'synced';
  }
};
