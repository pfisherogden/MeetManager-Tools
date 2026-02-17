import { Platform } from 'react-native';
import { DQ, Swimmer } from '../types';

// In-memory store for web mock
let mockDQs: DQ[] = [];

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
      name: `${gender} ${ageGroup} ${distance} ${stroke}`,
      isRelay: isRelay,
      stroke: isRelay ? 'Medley Relay' : stroke // Store stroke for sorting logic
    });

    // Generate 2 heats per event
    for (let h = 1; h <= 2; h++) {
      const heatId = heatIdCounter++;
      heats.push({ id: heatId, number: h, event_id: i });

      // Generate 4 swimmers per heat
      for (let l = 1; l <= 4; l++) {
        const swimmerId = swimmerIdCounter++;
        const relayMembers = isRelay ? [
          `Swimmer ${swimmerId}-1`,
          `Swimmer ${swimmerId}-2`,
          `Swimmer ${swimmerId}-3`,
          `Swimmer ${swimmerId}-4`
        ] : [];

        swimmers.push({
          id: swimmerId,
          heat_id: heatId,
          lane: l,
          name: `Swimmer ${swimmerId}`,
          team: l % 2 === 0 ? 'FAST' : 'SLOW',
          members: relayMembers
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
  const heat = _testData.heats.find(h => h.id === heatId);
  const event = heat ? _testData.events.find(e => e.id === heat.event_id) : null;
  const isRelay = event ? event.isRelay : false;

  const swimmers: Swimmer[] = _testData.swimmers.filter(s => s.heat_id === heatId);

  // Create a map for quick lookup
  const swimmerMap = new Map(swimmers.map(s => [s.lane, s]));

  const result: Swimmer[] = [];
  // Assume 6 lanes for now (could be dynamic based on event settings later)
  for (let lane = 1; lane <= 6; lane++) {
    if (swimmerMap.has(lane)) {
      const s = swimmerMap.get(lane)!;

      let dqCode: string | undefined = undefined;
      let relayDqs: DQ[] = [];

      if (isRelay) {
        relayDqs = mockDQs
          .filter(d => d.swimmerId === s.id)
          .map(d => ({ leg: d.leg, dq_code: d.dqCode, notes: d.notes }));
      } else {
        const dq = mockDQs.find(d => d.swimmerId === s.id);
        dqCode = dq ? dq.dqCode : undefined;
        const dqNote = dq ? dq.notes : undefined;
        result.push({
          ...s,
          dq_code: dqCode,
          notes: dqNote,
          relay_dqs: relayDqs,
          isRelay: isRelay,
          members: s.members || [],
          empty: false
        });
        continue;
      }

      result.push({
        ...s,
        dq_code: dqCode,
        relay_dqs: relayDqs,
        isRelay: isRelay,
        members: s.members || [],
        empty: false
      });
    } else {
      result.push({
        id: `empty-${heatId}-${lane}`,
        heat_id: heatId,
        lane: lane,
        name: 'Empty',
        team: '',
        dq_code: undefined,
        relay_dqs: [],
        isRelay: isRelay,
        empty: true
      });
    }
  }
  return result;
};

export const saveDQ = (eventId: number, swimmerId: number, dqCode: string, leg?: number, notes?: string) => {
  console.log('Web Mock DQ Saved:', { eventId, swimmerId, dqCode, leg, notes });

  // Call runSync to support test verification
  getDb().runSync(
    'INSERT INTO dqs (event_id, swimmer_id, dq_code, leg, notes, sync_status) VALUES (?, ?, ?, ?, ?, ?)',
    eventId,
    swimmerId,
    dqCode,
    leg || null,
    notes || undefined,
    'pending'
  );

  // Update in-memory store
  const existingIndex = mockDQs.findIndex(d => d.swimmerId === swimmerId && d.leg === leg);
  if (existingIndex >= 0) {
    mockDQs[existingIndex] = { dq_code: dqCode, leg, notes, swimmerId, eventId, timestamp: new Date().toISOString() };
  } else {
    mockDQs.push({ dq_code: dqCode, leg, notes, swimmerId, eventId, timestamp: new Date().toISOString() });
  }
  return { changes: 1 };
};

export const getPendingDQs = (): DQ[] => {
  // Return all as pending for mock purposes
  return mockDQs;
};

export const markAsSynced = (id: number) => { };
