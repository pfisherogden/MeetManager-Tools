import type { Meet, Team, Session, SwimEvent, Athlete, Entry, Relay, Score } from './swim-meet-types'

export const meets: Meet[] = [
  { id: 'm1', name: 'Summer Championships 2025', location: 'Aquatic Center, Miami', startDate: '2025-07-15', endDate: '2025-07-18', poolType: 'LCM', status: 'upcoming' },
  { id: 'm2', name: 'Regional Qualifiers', location: 'Olympic Pool, Tampa', startDate: '2025-06-20', endDate: '2025-06-22', poolType: 'SCY', status: 'upcoming' },
  { id: 'm3', name: 'Spring Invitational', location: 'University Pool, Orlando', startDate: '2025-04-10', endDate: '2025-04-12', poolType: 'SCY', status: 'completed' },
  { id: 'm4', name: 'State Finals 2024', location: 'State Aquatic Complex, Jacksonville', startDate: '2024-08-05', endDate: '2024-08-08', poolType: 'LCM', status: 'completed' },
  { id: 'm5', name: 'Winter Classic', location: 'Indoor Pool, Gainesville', startDate: '2025-01-15', endDate: '2025-01-17', poolType: 'SCY', status: 'completed' },
]

export const teams: Team[] = [
  { id: 't1', name: 'Miami Marlins', abbreviation: 'MIA', city: 'Miami', state: 'FL', athleteCount: 45, color: '#0077B6' },
  { id: 't2', name: 'Tampa Bay Sharks', abbreviation: 'TBS', city: 'Tampa', state: 'FL', athleteCount: 38, color: '#00B4D8' },
  { id: 't3', name: 'Orlando Waves', abbreviation: 'ORL', city: 'Orlando', state: 'FL', athleteCount: 52, color: '#48CAE4' },
  { id: 't4', name: 'Jacksonville Dolphins', abbreviation: 'JAX', city: 'Jacksonville', state: 'FL', athleteCount: 41, color: '#90E0EF' },
  { id: 't5', name: 'Gainesville Gators', abbreviation: 'GNV', city: 'Gainesville', state: 'FL', athleteCount: 36, color: '#023E8A' },
  { id: 't6', name: 'Fort Lauderdale Fins', abbreviation: 'FTL', city: 'Fort Lauderdale', state: 'FL', athleteCount: 29, color: '#0096C7' },
]

export const sessions: Session[] = [
  { id: 's1', meetId: 'm1', name: 'Prelims Day 1', date: '2025-07-15', warmUpTime: '07:00', startTime: '09:00', eventCount: 12 },
  { id: 's2', meetId: 'm1', name: 'Finals Day 1', date: '2025-07-15', warmUpTime: '16:00', startTime: '18:00', eventCount: 8 },
  { id: 's3', meetId: 'm1', name: 'Prelims Day 2', date: '2025-07-16', warmUpTime: '07:00', startTime: '09:00', eventCount: 14 },
  { id: 's4', meetId: 'm1', name: 'Finals Day 2', date: '2025-07-16', warmUpTime: '16:00', startTime: '18:00', eventCount: 10 },
  { id: 's5', meetId: 'm2', name: 'Timed Finals', date: '2025-06-20', warmUpTime: '08:00', startTime: '10:00', eventCount: 20 },
  { id: 's6', meetId: 'm3', name: 'Session A', date: '2025-04-10', warmUpTime: '07:30', startTime: '09:00', eventCount: 16 },
]

export const events: SwimEvent[] = [
  { id: 'e1', sessionId: 's1', eventNumber: 1, distance: 200, stroke: 'Freestyle', gender: 'F', ageGroup: '15-18', entryCount: 24 },
  { id: 'e2', sessionId: 's1', eventNumber: 2, distance: 200, stroke: 'Freestyle', gender: 'M', ageGroup: '15-18', entryCount: 28 },
  { id: 'e3', sessionId: 's1', eventNumber: 3, distance: 100, stroke: 'Backstroke', gender: 'F', ageGroup: '13-14', entryCount: 18 },
  { id: 'e4', sessionId: 's1', eventNumber: 4, distance: 100, stroke: 'Backstroke', gender: 'M', ageGroup: '13-14', entryCount: 22 },
  { id: 'e5', sessionId: 's1', eventNumber: 5, distance: 200, stroke: 'IM', gender: 'F', ageGroup: 'Open', entryCount: 32 },
  { id: 'e6', sessionId: 's1', eventNumber: 6, distance: 200, stroke: 'IM', gender: 'M', ageGroup: 'Open', entryCount: 30 },
  { id: 'e7', sessionId: 's1', eventNumber: 7, distance: 50, stroke: 'Butterfly', gender: 'F', ageGroup: '11-12', entryCount: 16 },
  { id: 'e8', sessionId: 's1', eventNumber: 8, distance: 50, stroke: 'Butterfly', gender: 'M', ageGroup: '11-12', entryCount: 14 },
  { id: 'e9', sessionId: 's2', eventNumber: 101, distance: 100, stroke: 'Freestyle', gender: 'F', ageGroup: '15-18', entryCount: 16 },
  { id: 'e10', sessionId: 's2', eventNumber: 102, distance: 100, stroke: 'Freestyle', gender: 'M', ageGroup: '15-18', entryCount: 16 },
]

export const athletes: Athlete[] = [
  { id: 'a1', firstName: 'Emma', lastName: 'Johnson', teamId: 't1', teamName: 'Miami Marlins', dateOfBirth: '2008-03-15', gender: 'F', age: 16 },
  { id: 'a2', firstName: 'Michael', lastName: 'Chen', teamId: 't1', teamName: 'Miami Marlins', dateOfBirth: '2007-08-22', gender: 'M', age: 17 },
  { id: 'a3', firstName: 'Sofia', lastName: 'Rodriguez', teamId: 't2', teamName: 'Tampa Bay Sharks', dateOfBirth: '2009-01-10', gender: 'F', age: 15 },
  { id: 'a4', firstName: 'James', lastName: 'Williams', teamId: 't2', teamName: 'Tampa Bay Sharks', dateOfBirth: '2006-11-05', gender: 'M', age: 18 },
  { id: 'a5', firstName: 'Olivia', lastName: 'Martinez', teamId: 't3', teamName: 'Orlando Waves', dateOfBirth: '2008-06-28', gender: 'F', age: 16 },
  { id: 'a6', firstName: 'David', lastName: 'Brown', teamId: 't3', teamName: 'Orlando Waves', dateOfBirth: '2007-04-12', gender: 'M', age: 17 },
  { id: 'a7', firstName: 'Isabella', lastName: 'Davis', teamId: 't4', teamName: 'Jacksonville Dolphins', dateOfBirth: '2009-09-03', gender: 'F', age: 15 },
  { id: 'a8', firstName: 'Ethan', lastName: 'Wilson', teamId: 't4', teamName: 'Jacksonville Dolphins', dateOfBirth: '2006-12-18', gender: 'M', age: 18 },
  { id: 'a9', firstName: 'Ava', lastName: 'Taylor', teamId: 't5', teamName: 'Gainesville Gators', dateOfBirth: '2008-02-07', gender: 'F', age: 16 },
  { id: 'a10', firstName: 'Noah', lastName: 'Anderson', teamId: 't5', teamName: 'Gainesville Gators', dateOfBirth: '2007-07-25', gender: 'M', age: 17 },
  { id: 'a11', firstName: 'Mia', lastName: 'Thomas', teamId: 't6', teamName: 'Fort Lauderdale Fins', dateOfBirth: '2010-05-14', gender: 'F', age: 14 },
  { id: 'a12', firstName: 'Lucas', lastName: 'Garcia', teamId: 't6', teamName: 'Fort Lauderdale Fins', dateOfBirth: '2008-10-30', gender: 'M', age: 16 },
]

export const entries: Entry[] = [
  { id: 'en1', eventId: 'e1', athleteId: 'a1', athleteName: 'Emma Johnson', teamName: 'Miami Marlins', seedTime: '2:05.34', finalTime: '2:04.12', place: 2 },
  { id: 'en2', eventId: 'e1', athleteId: 'a3', athleteName: 'Sofia Rodriguez', teamName: 'Tampa Bay Sharks', seedTime: '2:08.45', finalTime: '2:06.88', place: 4 },
  { id: 'en3', eventId: 'e1', athleteId: 'a5', athleteName: 'Olivia Martinez', teamName: 'Orlando Waves', seedTime: '2:03.22', finalTime: '2:02.55', place: 1 },
  { id: 'en4', eventId: 'e1', athleteId: 'a7', athleteName: 'Isabella Davis', teamName: 'Jacksonville Dolphins', seedTime: '2:10.11', finalTime: '2:08.33', place: 5 },
  { id: 'en5', eventId: 'e1', athleteId: 'a9', athleteName: 'Ava Taylor', teamName: 'Gainesville Gators', seedTime: '2:06.78', finalTime: '2:05.44', place: 3 },
  { id: 'en6', eventId: 'e2', athleteId: 'a2', athleteName: 'Michael Chen', teamName: 'Miami Marlins', seedTime: '1:52.45', finalTime: '1:51.22', place: 1 },
  { id: 'en7', eventId: 'e2', athleteId: 'a4', athleteName: 'James Williams', teamName: 'Tampa Bay Sharks', seedTime: '1:54.88', finalTime: '1:53.67', place: 3 },
  { id: 'en8', eventId: 'e2', athleteId: 'a6', athleteName: 'David Brown', teamName: 'Orlando Waves', seedTime: '1:53.12', finalTime: '1:52.44', place: 2 },
  { id: 'en9', eventId: 'e2', athleteId: 'a8', athleteName: 'Ethan Wilson', teamName: 'Jacksonville Dolphins', seedTime: '1:55.33', finalTime: '1:54.89', place: 4 },
  { id: 'en10', eventId: 'e2', athleteId: 'a10', athleteName: 'Noah Anderson', teamName: 'Gainesville Gators', seedTime: '1:56.22', finalTime: '1:55.78', place: 5 },
]

export const relays: Relay[] = [
  { id: 'r1', eventId: 'e9', teamId: 't1', teamName: 'Miami Marlins', leg1: 'Emma Johnson', leg2: 'Sofia Rodriguez', leg3: 'Olivia Martinez', leg4: 'Isabella Davis', seedTime: '3:52.34', finalTime: '3:50.12', place: 1 },
  { id: 'r2', eventId: 'e9', teamId: 't2', teamName: 'Tampa Bay Sharks', leg1: 'Ava Taylor', leg2: 'Mia Thomas', leg3: 'Emma Johnson', leg4: 'Sofia Rodriguez', seedTime: '3:55.67', finalTime: '3:53.44', place: 2 },
  { id: 'r3', eventId: 'e9', teamId: 't3', teamName: 'Orlando Waves', leg1: 'Isabella Davis', leg2: 'Ava Taylor', leg3: 'Mia Thomas', leg4: 'Olivia Martinez', seedTime: '3:58.22', finalTime: '3:56.88', place: 3 },
  { id: 'r4', eventId: 'e10', teamId: 't1', teamName: 'Miami Marlins', leg1: 'Michael Chen', leg2: 'James Williams', leg3: 'David Brown', leg4: 'Ethan Wilson', seedTime: '3:28.45', finalTime: '3:26.33', place: 1 },
  { id: 'r5', eventId: 'e10', teamId: 't2', teamName: 'Tampa Bay Sharks', leg1: 'Noah Anderson', leg2: 'Lucas Garcia', leg3: 'Michael Chen', leg4: 'James Williams', seedTime: '3:32.11', finalTime: '3:30.55', place: 2 },
  { id: 'r6', eventId: 'e10', teamId: 't4', teamName: 'Jacksonville Dolphins', leg1: 'David Brown', leg2: 'Ethan Wilson', leg3: 'Noah Anderson', leg4: 'Lucas Garcia', seedTime: '3:35.78', finalTime: '3:33.22', place: 3 },
]

export const scores: Score[] = [
  { id: 'sc1', meetId: 'm3', teamId: 't1', teamName: 'Miami Marlins', individualPoints: 245, relayPoints: 88, totalPoints: 333, rank: 1 },
  { id: 'sc2', meetId: 'm3', teamId: 't3', teamName: 'Orlando Waves', individualPoints: 212, relayPoints: 72, totalPoints: 284, rank: 2 },
  { id: 'sc3', meetId: 'm3', teamId: 't2', teamName: 'Tampa Bay Sharks', individualPoints: 198, relayPoints: 64, totalPoints: 262, rank: 3 },
  { id: 'sc4', meetId: 'm3', teamId: 't5', teamName: 'Gainesville Gators', individualPoints: 176, relayPoints: 56, totalPoints: 232, rank: 4 },
  { id: 'sc5', meetId: 'm3', teamId: 't4', teamName: 'Jacksonville Dolphins', individualPoints: 154, relayPoints: 48, totalPoints: 202, rank: 5 },
  { id: 'sc6', meetId: 'm3', teamId: 't6', teamName: 'Fort Lauderdale Fins', individualPoints: 122, relayPoints: 40, totalPoints: 162, rank: 6 },
]
