import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react-native';
import App from '../App';
import * as db from '../src/database/db';

jest.mock('expo-sqlite', () => ({
  openDatabaseSync: jest.fn(() => ({
    execSync: jest.fn(),
    runSync: jest.fn(() => ({ lastInsertRowId: 1, changes: 1 })),
    getAllSync: jest.fn((query) => {
      if (query.includes('FROM events')) return [{ id: 1, number: 1, name: 'Event 1' }];
      if (query.includes('FROM heats')) return [{ id: 10, number: 1, event_id: 1 }];
      if (query.includes('FROM swimmers')) return [{ id: 100, name: 'John Doe', lane: 1, team: 'T1' }];
      if (query.includes('FROM dqs')) return [];
      return [];
    }),
    getFirstSync: jest.fn(() => ({ count: 1 })),
  })),
}));

describe('User Journey: Record a DQ', () => {
  it('should allow a judge to navigate from events to a swimmer and record a DQ', async () => {
    render(<App />);

    // 1. View Event List
    expect(screen.getByText('Events')).toBeTruthy();
    expect(screen.getByText('Event 1')).toBeTruthy();

    // 2. Select Event
    fireEvent.press(screen.getByText('Event 1'));
    expect(screen.getByText('Heat 1')).toBeTruthy();

    // 3. Select Heat
    fireEvent.press(screen.getByText('Heat 1'));
    expect(screen.getByText('John Doe')).toBeTruthy();

    // 4. Tap Swimmer to DQ
    fireEvent.press(screen.getByText('TAP TO DQ'));
    expect(screen.getByText(/DQ Swimmer: John Doe/)).toBeTruthy();

    // 5. Select a DQ Code (e.g., 1A)
    fireEvent.press(screen.getByText('1A'));

    // 6. Verify we are back on judge screen and modal is closed
    expect(screen.queryByText('CANCEL')).toBeNull();
    expect(screen.getByText('John Doe')).toBeTruthy();
  });
});
