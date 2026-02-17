export interface Event {
  id: number;
  number: number;
  name: string;
  distance: number;
  stroke: string;
  isRelay: boolean;
}

export interface Heat {
  id: number;
  number: number;
  event_id: number;
}

export interface DQ {
    id: number;
    event_id: number;
    swimmer_id: number;
    dq_code: string;
    leg?: number;
    notes?: string;
    sync_status: 'pending' | 'synced';
    timestamp: string;
}

export interface DqCode {
    code: string;
    description: string;
}

export interface Swimmer {
  id: number;
  lane: number;
  name: string;
  team: string;
  heat_id: number;
  isRelay: boolean;
  members: string[];
  relay_dqs: DQ[];
  notes: string;
  dq_code: string;
  empty?: boolean;
}
