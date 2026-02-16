import { Platform } from 'react-native';

// In-memory store for web mock
let mockDQs: any[] = [];

const mockDb = {
  execSync: () => { },
  runSync: (query: string, ...params: any[]) => ({ lastInsertRowId: 1, changes: 1 }),
  getAllSync: (query: string, ...params: any[]) => [],
  getFirstSync: (query: string, ...params: any[]) => ({ count: 0 }),
};

export const getDb = () => {
  return mockDb;
};

export const initDatabase = () => { };
export const seedData = () => { };

// Helper to generate test data
const generateTestData = () => {
  const events = [];
  const heats = [];
  const swimmers = [];

  let heatIdCounter = 1;
  let swimmerIdCounter = 1;

  for (let i = 1; i <= 80; i++) {
    const isRelay = i % 4 === 0; // Every 4th event is a relay
    const gender = i % 2 !== 0 ? 'Girls' : 'Boys';
    const ageGroup = i > 40 ? '11-12' : '9-10';
    const distance = isRelay ? 200 : 50;
    const stroke = isRelay ? 'Medley Relay' : ['Free', 'Back', 'Breast', 'Fly'][i % 4];

    events.push({
      id: i,
      number: i,
      name: `${gender} ${ageGroup} ${distance} ${stroke}`
    });

    // Generate 2 heats per event
    for (let h = 1; h <= 2; h++) {
      const heatId = heatIdCounter++;
      heats.push({ id: heatId, number: h, event_id: i });

      // Generate 4 swimmers per heat
      for (let l = 1; l <= 4; l++) {
        const swimmerId = swimmerIdCounter++;
        swimmers.push({
          id: swimmerId,
          heat_id: heatId,
          lane: l,
          name: `Swimmer ${swimmerId}`,
          team: l % 2 === 0 ? 'FAST' : 'SLOW'
        });
      }
    }
  }
  return { events, heats, swimmers };
};

const _testData = generateTestData();

export const getEvents = () => _testData.events;

export const getHeatsByEvent = (eventId: number) => {
  return _testData.heats.filter(h => h.event_id === eventId);
};

export const getSwimmersByHeat = (heatId: number) => {
  const swimmers = _testData.swimmers.filter(s => s.heat_id === heatId);

  // Create a map for quick lookup
  const swimmerMap = new Map(swimmers.map(s => [s.lane, s]));

  const result = [];
  // Assume 6 lanes for now (could be dynamic based on event settings later)
  for (let lane = 1; lane <= 6; lane++) {
    if (swimmerMap.has(lane)) {
      const s = swimmerMap.get(lane)!;
      const dq = mockDQs.find(d => d.swimmerId === s.id);
      result.push({
        ...s,
        dq_code: dq ? dq.dqCode : null,
        empty: false
      });
    } else {
      result.push({
        id: `empty-${heatId}-${lane}`,
        heat_id: heatId,
        lane: lane,
        name: 'Empty',
        team: '',
        dq_code: null,
        empty: true
      });
    }
  }
  return result;
};

export const saveDQ = (eventId: number, swimmerId: number, dqCode: string) => {
  console.log('Web Mock DQ Saved:', { eventId, swimmerId, dqCode });

  // Call runSync to support test verification
  getDb().runSync(
    'INSERT INTO dqs (event_id, swimmer_id, dq_code, sync_status) VALUES (?, ?, ?, ?)',
    eventId,
    swimmerId,
    dqCode,
    'pending'
  );

  // Update in-memory store
  const existingIndex = mockDQs.findIndex(d => d.swimmerId === swimmerId);
  if (existingIndex >= 0) {
    mockDQs[existingIndex] = { eventId, swimmerId, dqCode, timestamp: new Date().toISOString() };
  } else {
    mockDQs.push({ eventId, swimmerId, dqCode, timestamp: new Date().toISOString() });
  }
  return { changes: 1 };
};

export const getPendingDQs = () => {
  // Return all as pending for mock purposes
  return mockDQs;
};

export const markAsSynced = (id: number) => { };
