import React, { useState, useEffect, useRef } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Platform, Dimensions } from 'react-native';
import { getHeatsByEvent, getSwimmersByHeat } from '../database/db';

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
    onSelectSwimmer: (swimmer: any, event: any, heat: any) => void;
    refreshTrigger: number; // Used to force re-render when DQs change
}

export const ProgramView: React.FC<ProgramViewProps> = ({ events, onSelectSwimmer, refreshTrigger }) => {
    const flatListRef = useRef<FlatList>(null);

    // Function to scroll to specific event index
    const scrollToEvent = (index: number) => {
        if (index < 0 || index >= events.length) return;
        flatListRef.current?.scrollToIndex({ index, animated: true });
    };

    const renderSwimmer = (swimmer: any, event: any, heat: any) => (
        <TouchableOpacity
            key={swimmer.id}
            style={styles.swimmerRow}
            onPress={() => onSelectSwimmer(swimmer, event, heat)}
        >
            <View style={styles.laneContainer}>
                <Text style={styles.laneText}>L{swimmer.lane}</Text>
            </View>
            <View style={styles.swimmerDetails}>
                <Text style={styles.swimmerName}>{swimmer.name}</Text>
                <Text style={styles.teamName}>{swimmer.team}</Text>
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

    const renderHeat = (heat: any, event: any) => {
        const swimmers = getSwimmersByHeat(heat.id);
        return (
            <View key={heat.id} style={styles.heatContainer}>
                <Text style={styles.heatHeader}>Heat {heat.number}</Text>
                {swimmers.map(swimmer => renderSwimmer(swimmer, event, heat))}
            </View>
        );
    };

    const renderEvent = ({ item, index }: { item: any; index: number }) => {
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
                initialNumToRender={3}
                maxToRenderPerBatch={5}
                windowSize={5}
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
        color: '#CCC',
        fontSize: 16,
        fontWeight: 'bold',
    }
});
