// mobile-judge-app/src/types.d.ts
export interface DQ {
  dq_code: string;
  notes?: string; // Make notes optional
  leg?: number;
}

export interface Swimmer {
  id: number;
  lane: number;
  name: string;
  team: string;
  heat_id: number;
  isRelay: boolean;
  members: string[];
  relay_dqs?: DQ[]; // Make relay_dqs optional
  dq_code?: string; // Add dq_code as optional
  notes?: string; // Make notes optional in Swimmer
  empty?: boolean;
}
