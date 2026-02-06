export interface Meet {
  id: string
  name: string
  location: string
  startDate: string
  endDate: string
  poolType: 'SCY' | 'SCM' | 'LCM'
  status: 'upcoming' | 'active' | 'completed'
}

export interface Team {
  id: string
  name: string
  abbreviation: string
  city: string
  state: string
  athleteCount: number
  color: string
}

export interface Session {
  id: string
  meetId: string
  name: string
  date: string
  warmUpTime: string
  startTime: string
  eventCount: number
}

export interface SwimEvent {
  id: string
  sessionId: string
  eventNumber: number
  distance: number
  stroke: string // Relaxed from specific union to allow server string
  gender: string
  ageGroup: string
  entryCount: number
}

export interface Athlete {
  id: string
  firstName: string
  lastName: string
  teamId: string
  teamName: string
  dateOfBirth: string
  gender: string
  age: number
}

export interface Entry {
  id: string
  eventId: string
  athleteId: string
  athleteName: string
  teamId: string // Added
  teamName: string
  seedTime: string
  finalTime: string | null
  place: number | null
  eventName?: string
  heat?: number
  lane?: number
  points?: number
}

export interface Relay {
  id: string
  eventId: string
  teamId: string
  teamName: string
  leg1: string
  leg2: string
  leg3: string
  leg4: string
  seedTime: string
  finalTime: string | null
  place: number | null
  eventName?: string
}

export interface EventScore {
  eventId: string
  eventName: string
  entries: Entry[]
}

export interface Score {
  id: string
  meetId: string
  teamId: string
  teamName: string
  individualPoints: number
  relayPoints: number
  totalPoints: number
  rank: number
}
