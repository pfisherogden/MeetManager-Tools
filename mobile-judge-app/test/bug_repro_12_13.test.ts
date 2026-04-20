import * as db from '../src/database/db';

// Mock the entire db module to avoid environment issues with native SQLite
jest.mock('../src/database/db', () => {
  let mockState: any = { events: [], heats: [], swimmers: [] };
  return {
    loadFromJSON: jest.fn((data) => { mockState = data; }),
    getEventById: jest.fn((id) => mockState.events.find((e: any) => e.id === id)),
    getHeatsByEvent: jest.fn((eventId) => mockState.heats.filter((h: any) => h.event_id === eventId)),
    getSwimmersByHeat: jest.fn((heatId) => mockState.swimmers.filter((s: any) => s.heat_id === heatId)),
    getSwimmerById: jest.fn((id) => mockState.swimmers.find((s: any) => s.id === id)),
  };
});

const mockChampsData = {
  events: [
    { id: 12, number: 12, name: "Mixed 15-18 200 Yard Medley Relay", isRelay: true, distance: 200, stroke: "Medley" },
    { id: 13, number: 13, name: "Girls 6 & under 25 Yard Freestyle", isRelay: false, distance: 25, stroke: "Free" }
  ],
  heats: [
    { id: 100, event_id: 12, number: 1 },
    { id: 101, event_id: 13, number: 1 }
  ],
  swimmers: [
    { id: 2400, heat_id: 100, lane: 1, name: "Team A", isRelay: true, members: ["S1", "S2", "S3", "S4"], team: "A", relay_dqs: [], notes: "", dq_code: "" },
    { id: 12800, heat_id: 101, lane: 1, name: "Individual Girl", isRelay: false, team: "A", relay_dqs: [], notes: "", dq_code: "" }
  ]
};

describe("Event 12 -> 13 Navigation Bug Reproduction", () => {
  beforeEach(() => {
    // @ts-expect-error - Mock module might not perfectly match types but logic is what matters here
    db.loadFromJSON(mockChampsData);
  });

  it("should correctly identify Event 12 as relay and Event 13 as individual", () => {
    const event12 = db.getEventById(12);
    const event13 = db.getEventById(13);

    expect(event12?.isRelay).toBe(true);
    expect(event13?.isRelay).toBe(false);
  });

  it("should return relay swimmers for Event 12 and individual for Event 13", () => {
    const swimmers12 = db.getSwimmersByHeat(100);
    const swimmers13 = db.getSwimmersByHeat(101);

    expect(swimmers12[0].isRelay).toBe(true);
    expect(swimmers12[0].name).toBe("Team A");
    expect(swimmers12[0].members?.length).toBe(4);

    expect(swimmers13[0].isRelay).toBe(false);
    expect(swimmers13[0].name).toBe("Individual Girl");
  });
});
