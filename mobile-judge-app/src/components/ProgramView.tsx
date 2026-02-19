import type React from 'react';
import { useRef } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, } from 'react-native';
import { getHeatsByEvent, getSwimmersByHeat } from '../database/db';
import type { Event, Heat, Swimmer, DQ } from '../types';

const COLORS = {
    background: '#FFFFFF',
    text: '#000000',
    primary: '#000000',
    secondary: '#555555',
    accent: '#E63946',
    white: '#FFFFFF',
    lightGray: '#F0F0F0',
    heatHeader: '#E0E0E0',
    icon: '#FFFFFF',
};

interface ProgramViewProps {
    events: any[];
    onSelectSwimmer: (swimmer: Swimmer, event: any, heat: any, leg?: number) => void;
    refreshTrigger: number; // Used to force re-render when DQs change
}

export const ProgramView: React.FC<ProgramViewProps> = ({ events, onSelectSwimmer, refreshTrigger }) => {
    const flatListRef = useRef<FlatList>(null);

    // Function to scroll to specific event index
    const scrollToEvent = (index: number) => {
        if (index < 0 || index >= events.length) return;
        flatListRef.current?.scrollToIndex({ index, animated: true, viewPosition: 0 });
    };

    const renderSwimmer = (swimmer: Swimmer, event: any, heat: any) => {
        const isRelay = swimmer.isRelay;

        if (isRelay) {
            if (swimmer.empty) return null; // Issue #81: Hide empty lanes for relays
            return (
                <View key={swimmer.id} style={[styles.swimmerRow, styles.relayRow]}>
                    <View style={styles.laneContainer}>
                        <Text style={styles.laneText}>L{swimmer.lane}</Text>
                    </View>
                    <View style={styles.swimmerDetails}>
                        <Text style={styles.teamName}>Team {swimmer.team}</Text>
                        <View style={styles.legsContainer}>
                            {[1, 2, 3, 4].map(leg => {
                                const dq = swimmer.relay_dqs?.find((d: DQ) => d.leg === leg);
                                const legName = swimmer.members?.[leg - 1] ? swimmer.members[leg - 1] : `Leg ${leg}`;
                                return (
                                    <TouchableOpacity
                                        key={leg}
                                        style={styles.legItem}
                                        onPress={() => onSelectSwimmer(swimmer, event, heat, leg)}
                                    >
                                        <View style={{ flex: 1 }}>
                                            <Text style={styles.legName}>{legName}</Text>
                                            {dq?.notes ? (
                                                <Text style={styles.notePreview} numberOfLines={1}>
                                                    {dq.notes}
                                                </Text>
                                            ) : null}
                                        </View>
                                        <Text style={[styles.legDq, !dq && { color: COLORS.secondary }]}>
                                            {dq ? dq.dq_code : 'DQ'}
                                        </Text>
                                    </TouchableOpacity>
                                );
                            })}
                        </View>
                    </View>
                </View>
            );
        }

        return (
            <TouchableOpacity
                key={swimmer.id}
                style={[styles.swimmerRow, swimmer.empty && styles.emptyRow]}
                onPress={() => onSelectSwimmer(swimmer, event, heat)}
            >
                <View style={[styles.laneContainer, swimmer.empty && styles.emptyLane]}>
                    <Text style={styles.laneText}>L{swimmer.lane}</Text>
                </View>
                <View style={styles.swimmerDetails}>
                    <Text style={[styles.swimmerName, swimmer.empty && styles.emptyText]}>{swimmer.name}</Text>
                    <Text style={styles.teamName}>{swimmer.team}</Text>
                    {swimmer.notes ? (
                        <Text style={styles.notePreview} numberOfLines={1}>
                            {swimmer.notes}
                        </Text>
                    ) : null}
                </View>
                <View style={styles.dqContainer}>
                    {swimmer.dq_code ? (
                        <Text style={styles.dqText}>{swimmer.dq_code}</Text>
                    ) : (
                        <Text style={styles.dqPlaceholder}>DQ</Text>
                    )}
                </View>
            </TouchableOpacity>
        );
    };

    const renderHeat = (heat: Heat, event: Event) => {
        const swimmers = getSwimmersByHeat(heat.id);
        return (
            <View key={heat.id} style={styles.heatContainer}>
                <Text style={styles.heatHeader}>Heat {heat.number}</Text>
                {swimmers.map(swimmer => renderSwimmer(swimmer, event, heat))}
            </View>
        );
    };

    const renderEvent = ({ item, index }: { item: Event; index: number }) => {
        const heats = getHeatsByEvent(item.id);
        return (
            <View style={styles.eventContainer}>
                <View style={styles.eventHeader}>
                    <Text style={styles.eventTitle}>
                        #{item.number} {item.name}
                    </Text>
                    <View style={styles.navIcons}>
                        <TouchableOpacity
                            onPress={() => scrollToEvent(index - 1)}
                            disabled={index === 0}
                            style={[styles.iconButton, index === 0 && styles.disabledIcon]}
                        >
                            <Text style={styles.iconText}>▲</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            onPress={() => scrollToEvent(index + 1)}
                            disabled={index === events.length - 1}
                            style={[styles.iconButton, index === events.length - 1 && styles.disabledIcon]}
                        >
                            <Text style={styles.iconText}>▼</Text>
                        </TouchableOpacity>
                    </View>
                </View>
                {heats.map(heat => renderHeat(heat, item))}
            </View>
        );
    };

    return (
        <View style={styles.container}>
            <FlatList
                ref={flatListRef}
                data={events}
                keyExtractor={(item) => item.id.toString()}
                renderItem={renderEvent}
                initialNumToRender={10}
                maxToRenderPerBatch={10}
                windowSize={21}
                extraData={refreshTrigger}
                onScrollToIndexFailed={(info) => {
                    const wait = new Promise(resolve => setTimeout(resolve, 500));
                    wait.then(() => {
                        flatListRef.current?.scrollToIndex({ index: info.index, animated: true });
                    });
                }}
            />
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: COLORS.background,
    },
    eventContainer: {
        marginBottom: 20,
        borderBottomWidth: 4,
        borderBottomColor: COLORS.primary,
    },
    eventHeader: {
        backgroundColor: COLORS.primary,
        padding: 15,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    eventTitle: {
        color: COLORS.white,
        fontSize: 20,
        fontWeight: 'bold',
        flex: 1,
    },
    navIcons: {
        flexDirection: 'row',
    },
    iconButton: {
        paddingHorizontal: 15,
        paddingVertical: 5,
    },
    iconText: {
        color: COLORS.icon,
        fontSize: 24,
        fontWeight: 'bold',
    },
    disabledIcon: {
        opacity: 0.3,
    },
    heatContainer: {
        paddingBottom: 10,
    },
    heatHeader: {
        backgroundColor: COLORS.heatHeader,
        padding: 10,
        fontSize: 18,
        fontWeight: 'bold',
        color: COLORS.text,
    },
    swimmerRow: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 15,
        borderBottomWidth: 1,
        borderBottomColor: COLORS.lightGray,
    },
    laneContainer: {
        width: 50,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: COLORS.secondary,
        borderRadius: 8,
        padding: 5,
        marginRight: 15,
    },
    laneText: {
        color: COLORS.white,
        fontSize: 18,
        fontWeight: 'bold',
    },
    swimmerDetails: {
        flex: 1,
    },
    swimmerName: {
        fontSize: 20,
        fontWeight: 'bold',
        color: COLORS.text,
    },
    teamName: {
        fontSize: 16,
        color: COLORS.secondary,
    },
    dqContainer: {
        width: 60,
        alignItems: 'center',
        justifyContent: 'center',
        borderLeftWidth: 1,
        borderLeftColor: COLORS.lightGray,
        paddingLeft: 10,
    },
    dqText: {
        color: COLORS.accent,
        fontSize: 22,
        fontWeight: '900',
    },
    dqPlaceholder: {
        color: COLORS.secondary,
        fontSize: 16,
        fontWeight: 'bold',
    },
    relayRow: {
        alignItems: 'flex-start',
    },
    legsContainer: {
        marginTop: 5,
        paddingLeft: 10,
        borderLeftWidth: 3,
        borderLeftColor: COLORS.accent,
        backgroundColor: '#FCFCFC',
        borderRadius: 4,
        width: '100%',
    },
    legItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#F0F0F0',
        paddingRight: 10,
    },
    legName: {
        fontSize: 16,
        fontWeight: 'bold',
        color: COLORS.text,
    },
    legDq: {
        fontSize: 16,
        fontWeight: '900',
        color: COLORS.accent,
    },
    emptyRow: {
        opacity: 0.6,
    },
    emptyLane: {
        backgroundColor: '#CCC',
    },
    emptyText: {
        color: '#999',
        fontStyle: 'italic',
    },
    notePreview: {
        fontSize: 12,
        color: COLORS.secondary,
        fontStyle: 'italic',
        marginTop: 2,
    }
});
