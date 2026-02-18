import { render, screen, fireEvent, waitForElementToBeRemoved } from '@testing-library/react-native';
import App from '../App';

jest.mock('../src/services/dataLoader', () => ({
  loadDataFromUrl: jest.fn(() => Promise.resolve({ loaded: false, dqData: null, syncUrl: null })),
}));

jest.mock('../src/database/db', () => ({
  initDatabase: jest.fn(),
  seedData: jest.fn(),
  getEvents: jest.fn(() => ([
    { id: 1, number: 1, name: 'Event 1', distance: 100, stroke: 'Freestyle', isRelay: false }
  ])),
  getHeatsByEvent: jest.fn((eventId) => ([
    { id: 10, number: 1, event_id: eventId }
  ])),
  getSwimmersByHeat: jest.fn((heatId) => ([
    { id: 100, name: 'John Doe', lane: 1, team: 'T1', heat_id: heatId, isRelay: false, members: [], relay_dqs: [], notes: '', dq_code: '' }
  ])),
  saveDQ: jest.fn(() => ({ changes: 1 })),
  getPendingDQs: jest.fn(() => []),
  markAsSynced: jest.fn(),
}));

jest.mock('@react-native-community/netinfo', () => ({
  fetch: jest.fn(() => Promise.resolve({ isConnected: true, isInternetReachable: true })),
  addEventListener: jest.fn(() => jest.fn()),
}));

describe('User Journey: Record a DQ', () => {
  beforeEach(() => {
    // Clear mocks before each test to ensure isolation
    jest.clearAllMocks();
  });

  it('should allow a judge to navigate from events to a swimmer and record a DQ', async () => {
    render(<App />);
    await waitForElementToBeRemoved(() => screen.getByTestId('loading-indicator'));

    // 1. View Event List
    expect(screen.getByText('Events')).toBeTruthy();
    expect(screen.getAllByText('Event 1')[0]).toBeTruthy();

    // 2. Select Event
    fireEvent.press(screen.getAllByText('Event 1')[0]);
    expect(screen.getByText('Heat 1')).toBeTruthy();

    // 3. Select Heat
    fireEvent.press(screen.getByText('Heat 1'));
    expect(screen.getByText('John Doe')).toBeTruthy();

    // 4. Tap Swimmer to DQ
    fireEvent.press(screen.getByText('TAP TO DQ'));
    expect(screen.getByText(/DQ: John Doe/)).toBeTruthy();

    // 5. Select a DQ Code (e.g., 1A)
    fireEvent.press(screen.getByText('1A'));

    // 6. Verify we are back on judge screen and modal is closed
    expect(screen.queryByText('CANCEL')).toBeNull();
    expect(screen.getByText('John Doe')).toBeTruthy();
  });
});
