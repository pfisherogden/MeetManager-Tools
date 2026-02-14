import { Platform } from 'react-native';

export const getDb = () => {
  return {
    execSync: () => {},
    runSync: () => ({ lastInsertRowId: 1, changes: 1 }),
    getAllSync: (query: string) => [],
    getFirstSync: () => ({ count: 0 }),
  };
};

export const initDatabase = () => {};
export const seedData = () => {};

export const getEvents = () => {
  return [
    { id: 1, number: 1, name: 'Girls 8&U 100 Medley Relay' },
    { id: 2, number: 2, name: 'Boys 8&U 100 Medley Relay' }
  ];
};

export const getHeatsByEvent = (eventId: number) => {
  return [{ id: 1, number: 1, event_id: eventId }];
};

export const getSwimmersByHeat = (heatId: number) => {
  return [
    { id: 1, lane: 1, name: 'Alice Smith', team: 'FAST' },
    { id: 2, lane: 2, name: 'Bob Jones', team: 'FAST' }
  ];
};

export const saveDQ = (eventId: number, swimmerId: number, dqCode: string) => {
  console.log('Web Mock DQ Saved:', { eventId, swimmerId, dqCode });
  return { changes: 1 };
};

export const getPendingDQs = () => [];
export const markAsSynced = (id: number) => {};
