import { Platform } from 'react-native';
import type { Event, Heat, Swimmer, DQ } from '../types';

// Web Mock State
let mockEvents: Event[] = [];
let mockHeats: Heat[] = [];
let mockSwimmers: Swimmer[] = [];
let mockDQs: DQ[] = [];

export const getDb = () => {
  return {
    execSync: () => {},
    runSync: () => ({ lastInsertRowId: 1, changes: 1 }),
    getAllSync: (_query: string) => [],
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

export const loadFromJSON = (programData: { events: Event[], heats: Heat[], swimmers: Swimmer[]}) => {
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
      { id: 1, number: 1, name: 'Girls 8&U 100 Medley Relay', distance: 100, stroke: 'Medley', isRelay: true },
      { id: 2, number: 2, name: 'Boys 8&U 100 Medley Relay', distance: 100, stroke: 'Medley', isRelay: true }
    ] as Event[];
    
    mockHeats = [
      { id: 1, number: 1, event_id: 1 }
    ];

    mockSwimmers = [
      { id: 1, lane: 1, name: 'Alice Smith', team: 'FAST', heat_id: 1, isRelay: false, members: [], relay_dqs: [], notes: '', dq_code: '' },
      { id: 2, lane: 2, name: 'Bob Jones', team: 'FAST', heat_id: 1, isRelay: false, members: [], relay_dqs: [], notes: '', dq_code: '' }
    ] as Swimmer[];
  }
};

export const getEvents = (): Event[] => {
  return mockEvents.sort((a, b) => a.number - b.number);
};

export const getHeatsByEvent = (eventId: number): Heat[] => {
  return mockHeats
    .filter(h => h.event_id === eventId)
    .sort((a, b) => a.number - b.number);
};

export const getSwimmersByHeat = (heatId: number): Swimmer[] => {
  const heatSwimmers = mockSwimmers
    .filter(s => s.heat_id === heatId)
    .sort((a, b) => a.lane - b.lane);

  const event = mockEvents.find(e => e.id === mockHeats.find(h => h.id === heatId)?.event_id);
  
  if (event?.isRelay) {
    return heatSwimmers.map(s => {
      const relayDQs = mockDQs.filter(dq => dq.swimmer_id === s.id && dq.leg);
      return { ...s, relay_dqs: relayDQs };
    });
  }
  
  return heatSwimmers.map(s => {
    const individualDQ = mockDQs.find(dq => dq.swimmer_id === s.id && !dq.leg);
    return { ...s, dq_code: individualDQ?.dq_code, notes: individualDQ?.notes };
  });
};

export const saveDQ = (eventId: number, swimmerId: number, dqCode: string, leg?: number, notes?: string) => {
  console.log('Web Mock DQ Saved:', { eventId, swimmerId, dqCode, leg, notes });
  
  // For relays, remove existing DQ for the same leg if it exists
  if (leg) {
    mockDQs = mockDQs.filter(dq => !(dq.swimmer_id === swimmerId && dq.leg === leg));
  } else {
    mockDQs = mockDQs.filter(dq => !(dq.swimmer_id === swimmerId && !dq.leg));
  }
  
  const newDQ: DQ = {
    id: mockDQs.length + 1,
    event_id: eventId,
    swimmer_id: swimmerId,
    dq_code: dqCode,
    leg,
    notes,
    sync_status: 'pending',
    timestamp: new Date().toISOString()
  };
  
  mockDQs.push(newDQ);
  return { changes: 1 };
};


export const getPendingDQs = (): DQ[] => {
  return mockDQs.filter(dq => dq.sync_status === 'pending');
};

export const markAsSynced = (id: number) => {
  const dq = mockDQs.find(d => d.id === id);
  if (dq) {
    dq.sync_status = 'synced';
  }
};
