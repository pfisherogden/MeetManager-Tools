import { useState, useEffect } from 'react';
import sampleData from '../../assets/data/sample_data.json';

// Types reflecting the UI needs
export interface SwimmerEntry {
    id: number;
    lane: number;
    name: string;
    team: string;
    relayLetter?: string;
    relayNames?: string[]; // Array of swimmer names for relays
    isRelay: boolean;
    seedTime: number;
    finalTime: number;
    finalPlace: number;
    dqCode: string | null;
    empty?: boolean;
    heat: number;
}

export interface Heat {
    id: number;
    number: number;
    entries: SwimmerEntry[];
}

export interface MeetingEvent {
    id: number;
    number: number;
    name: string;
    heats: Heat[];
}

// Raw Data Types (Partial)
interface RawEvent {
    Event_no: number;
    Event_ltr: string;
    Event_dist: number;
    Event_stroke: string;
    Event_sex: string;
    Low_age: number;
    High_Age: number;
    Ind_rel: string; // 'I' or 'R'
    Event_ptr: number; // PK
}

interface RawEntry {
    Event_ptr: number;
    Ath_no: number;
    Fin_heat: number;
    Fin_lane: number;
    ActualSeed_time: number;
    Fin_Time: number;
    Fin_place: number;
    Fin_dqcode: string | null; // Note: In JSON it might be "Fin_dqcode": NaN or "Fin_dqcode": "1C"
}

interface RawRelay {
    Event_ptr: number;
    Relay_no: number; // ID
    Team_no: number;
    Team_ltr: string;
    Fin_heat: number;
    Fin_lane: number;
    ActualSeed_time: number;
    Fin_Time: number;
    Fin_place: number;
    Fin_dqcode: string | null;
}

interface RawAthlete {
    Ath_no: number;
    First_name: string;
    Last_name: string;
    Team_no: number;
}

interface RawRelayName {
    Relay_no: number;
    Pos_no: number;
    Ath_no: number;
}

interface RawTeam {
    Team_no: number;
    Team_abbr: string;
    Team_name: string;
}

const getStrokeName = (code: string) => {
    const map: Record<string, string> = {
        'A': 'Freestyle', 'B': 'Backstroke', 'C': 'Breaststroke', 'D': 'Butterfly', 'E': 'Medley'
    };
    return map[code] || code;
};

const getEventName = (evt: RawEvent) => {
    const gender = evt.Event_sex === 'M' ? 'Boys' : (evt.Event_sex === 'F' ? 'Girls' : 'Mixed');
    const age = evt.High_Age === 0 ? 'Open' : (evt.Low_age === 0 ? `${evt.High_Age}&U` : `${evt.Low_age}-${evt.High_Age}`);
    const stroke = getStrokeName(evt.Event_stroke);
    const type = evt.Ind_rel === 'R' ? 'Relay' : '';
    return `${gender} ${age} ${evt.Event_dist} ${stroke} ${type}`.trim();
};

export const useMeetData = () => {
    const [events, setEvents] = useState<MeetingEvent[]>([]);
    const [isResults, setIsResults] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // In a real app, you might fetch this. Here we parse the imported JSON.
        const parseData = () => {
            try {
                const raw = (sampleData as any).data;

                // 1. Map Teams and Athletes
                const teams = new Map<number, string>();
                raw.Team.forEach((t: RawTeam) => teams.set(t.Team_no, t.Team_abbr));

                const athletes = new Map<number, { name: string, teamId: number }>();
                raw.Athlete.forEach((a: RawAthlete) => {
                    athletes.set(a.Ath_no, {
                        name: `${a.First_name} ${a.Last_name}`,
                        teamId: a.Team_no
                    });
                });

                // 2. Process Events
                const parsedEvents: MeetingEvent[] = raw.Event.map((evt: RawEvent) => {
                    const isRelay = evt.Ind_rel === 'R';
                    let entries: SwimmerEntry[] = [];

                    if (isRelay) {
                        // Process Relays
                        const relays = raw.Relay.filter((r: RawRelay) => r.Event_ptr === evt.Event_ptr);

                        entries = relays.map((r: RawRelay) => {
                            // Find relay swimmers
                            const relaySwimmers = raw.RelayNames
                                ? raw.RelayNames.filter((rn: RawRelayName) => rn.Relay_no === r.Relay_no)
                                : [];

                            // Sort by position and map to names
                            const names = relaySwimmers
                                .sort((a: RawRelayName, b: RawRelayName) => a.Pos_no - b.Pos_no)
                                .map((rn: RawRelayName) => {
                                    const ath = athletes.get(rn.Ath_no);
                                    return ath ? ath.name : 'Unknown';
                                });

                            return {
                                id: r.Relay_no,
                                lane: r.Fin_lane,
                                name: '', // Relay team name constructed in UI or here
                                team: teams.get(r.Team_no) || 'Unknown',
                                relayLetter: r.Team_ltr,
                                relayNames: names.length > 0 ? names : undefined,
                                isRelay: true,
                                seedTime: r.ActualSeed_time,
                                finalTime: r.Fin_Time,
                                finalPlace: r.Fin_place,
                                dqCode: r.Fin_dqcode && r.Fin_dqcode !== 'NaN' ? r.Fin_dqcode : null,
                                heat: r.Fin_heat
                            };
                        });
                    } else {
                        // Process Individual Entries
                        const inds = raw.Entry.filter((e: RawEntry) => e.Event_ptr === evt.Event_ptr);
                        entries = inds.map((e: RawEntry, idx: number) => {
                            const ath = athletes.get(e.Ath_no);
                            return {
                                id: e.Ath_no * 1000 + idx, // synthetic unique id
                                lane: e.Fin_lane,
                                name: ath ? ath.name : 'Unknown Athlete',
                                team: ath ? (teams.get(ath.teamId) || '') : '',
                                isRelay: false,
                                seedTime: e.ActualSeed_time,
                                finalTime: e.Fin_Time,
                                finalPlace: e.Fin_place,
                                dqCode: e.Fin_dqcode && e.Fin_dqcode !== 'NaN' ? e.Fin_dqcode : null,
                                heat: e.Fin_heat
                            };
                        });
                    }

                    // Check if entries exist
                    if (entries.length === 0) return null;

                    // Group by Heat
                    const heatsMap = new Map<number, SwimmerEntry[]>();
                    entries.forEach((e: SwimmerEntry) => {
                        if (!heatsMap.has(e.heat)) heatsMap.set(e.heat, []);
                        heatsMap.get(e.heat)?.push(e);
                    });

                    const heats: Heat[] = Array.from(heatsMap.entries()).map(([num, entries]) => ({
                        id: num, // simple heat id
                        number: num,
                        entries: entries.sort((a, b) => a.lane - b.lane)
                    })).sort((a, b) => a.number - b.number);

                    return {
                        id: evt.Event_ptr,
                        number: evt.Event_no,
                        name: getEventName(evt),
                        heats
                    };
                }).filter((e: MeetingEvent | null): e is MeetingEvent => e !== null);

                // Sort events by number
                parsedEvents.sort((a, b) => a.number - b.number);

                // Check if this is a results file by looking for any final times
                let hasResults = false;
                for (const evt of parsedEvents) {
                    for (const heat of evt.heats) {
                        if (heat.entries.some(e => e.finalTime > 0 || e.dqCode !== null)) {
                            hasResults = true;
                            break;
                        }
                    }
                    if (hasResults) break;
                }

                setEvents(parsedEvents);
                setIsResults(hasResults);
                setLoading(false);
            } catch (err) {
                console.error("Failed to parse meet data:", err);
                setLoading(false);
            }
        };

        setTimeout(parseData, 0);
    }, []);

    return { events, isResults, loading };
};
