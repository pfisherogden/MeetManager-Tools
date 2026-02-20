import React, { useRef } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../constants/colors';

interface Heat {
    id: number | string;
    number: number;
    entries: any[]; // You might want to define a more specific type for entries if available
}

interface Event {
    id: number | string;
    number: number;
    name: string;
    heats: Heat[];
}

interface ProgramListProps {
    events: Event[];
    onEventChanged?: (event: Event) => void;
}

export const ProgramList: React.FC<ProgramListProps> = ({ events, onEventChanged }) => {
    const flatListRef = useRef<FlatList>(null);

    const scrollToEvent = (index: number) => {
        if (index < 0 || index >= events.length) return;
        flatListRef.current?.scrollToIndex({ index, animated: true, viewPosition: 0 });
    };

    const getResultColor = (entry: any) => {
        if (entry.dqCode) return COLORS.accent; // Red for DQ
        return COLORS.text;
    };

    const formatTime = (time: number) => {
        if (!time || time === 0) return 'NT';
        return time.toFixed(2);
    };

    const renderSwimmer = (entry: any) => {
        if (entry.empty) return null; // Skip empty lanes if data has them marked

        const isRelay = entry.isRelay;
        const name = isRelay ? `Team ${entry.team} ${entry.relayLetter || ''}` : entry.name;
        const team = isRelay ? '' : entry.team;

        // Result display logic
        const hasResult = entry.finalTime > 0 || entry.dqCode;
        const resultText = entry.dqCode ? entry.dqCode : (entry.finalTime > 0 ? formatTime(entry.finalTime) : '');
        const placeText = entry.finalPlace > 0 ? `${entry.finalPlace}` : '-';

        return (
            <View key={entry.id} style={styles.swimmerRow}>
                <View style={styles.laneContainer}>
                    <Text style={styles.laneText}>L{entry.lane}</Text>
                </View>

                <View style={styles.swimmerDetails}>
                    <Text style={styles.swimmerName}>{name}</Text>
                    {!!team && <Text style={styles.teamName}>{team}</Text>}
                    <Text style={styles.seedTime}>Seed: {formatTime(entry.seedTime)}</Text>
                </View>

                <View style={styles.resultContainer}>
                    {hasResult ? (
                        <>
                            <Text style={[styles.resultTime, { color: getResultColor(entry) }]}>
                                {resultText}
                            </Text>
                            {!entry.dqCode && (
                                <Text style={styles.resultPlace}>Pl: {placeText}</Text>
                            )}
                        </>
                    ) : (
                        <Text style={styles.noResult}>-</Text>
                    )}
                </View>
            </View>
        );
    };

    const renderHeat = (heat: any, event: any) => {
        return (
            <View key={heat.id} style={styles.heatContainer}>
                <Text style={styles.heatHeader}>Heat {heat.number}</Text>
                {heat.entries.map((entry: any) => renderSwimmer(entry))}
            </View>
        );
    };

    const renderEvent = ({ item, index }: { item: any; index: number }) => {
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
                            <Ionicons name="chevron-up" size={24} color={COLORS.icon} />
                        </TouchableOpacity>
                        <TouchableOpacity
                            onPress={() => scrollToEvent(index + 1)}
                            disabled={index === events.length - 1}
                            style={[styles.iconButton, index === events.length - 1 && styles.disabledIcon]}
                        >
                            <Ionicons name="chevron-down" size={24} color={COLORS.icon} />
                        </TouchableOpacity>
                    </View>
                </View>
                {item.heats.map((heat: any) => renderHeat(heat, item))}
            </View>
        );
    };

    const onViewableItemsChanged = useRef(({ viewableItems }: any) => {
        if (viewableItems.length > 0 && onEventChanged) {
            onEventChanged(viewableItems[0].item);
        }
    }).current;

    return (
        <View style={styles.container}>
            <FlatList
                ref={flatListRef}
                data={events}
                keyExtractor={(item) => item.id.toString()}
                renderItem={renderEvent}
                initialNumToRender={5}
                maxToRenderPerBatch={5}
                windowSize={11}
                onViewableItemsChanged={onViewableItemsChanged}
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
        position: 'sticky' as any, // Web support
        top: 0,
        zIndex: 10,
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
        paddingHorizontal: 10,
    },
    disabledIcon: {
        opacity: 0.3,
    },
    heatContainer: {
        paddingBottom: 10,
    },
    heatHeader: {
        backgroundColor: COLORS.heatHeader,
        padding: 8,
        fontSize: 16,
        fontWeight: 'bold',
        color: COLORS.text,
    },
    swimmerRow: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        borderBottomWidth: 1,
        borderBottomColor: COLORS.lightGray,
    },
    laneContainer: {
        width: 40,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: COLORS.secondary,
        borderRadius: 4,
        padding: 4,
        marginRight: 10,
    },
    laneText: {
        color: COLORS.white,
        fontSize: 16,
        fontWeight: 'bold',
    },
    swimmerDetails: {
        flex: 1,
    },
    swimmerName: {
        fontSize: 18,
        fontWeight: 'bold',
        color: COLORS.text,
    },
    teamName: {
        fontSize: 14,
        color: COLORS.secondary,
    },
    seedTime: {
        fontSize: 12,
        color: '#888',
        marginTop: 2,
    },
    resultContainer: {
        minWidth: 80,
        alignItems: 'flex-end',
    },
    resultTime: {
        fontSize: 18,
        fontWeight: 'bold',
        color: COLORS.text,
    },
    resultPlace: {
        fontSize: 12,
        color: COLORS.secondary,
    },
    noResult: {
        fontSize: 18,
        color: '#CCC',
    },
});
