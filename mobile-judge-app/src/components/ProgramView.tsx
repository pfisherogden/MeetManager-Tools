import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Platform } from 'react-native';
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
};

interface ProgramViewProps {
    events: any[];
    onSelectSwimmer: (swimmer: any, event: any, heat: any) => void;
    refreshTrigger: number; // Used to force re-render when DQs change
}

export const ProgramView: React.FC<ProgramViewProps> = ({ events, onSelectSwimmer, refreshTrigger }) => {
    // We render a single FlatList of events.
    // Each event item renders its own heats and swimmers.
    // Note: For 80 events * ~8 swimmers, this is ~640 items. 
    // Nested FlatLists can be tricky, so we'll render Heats/Swimmers as standard Views inside the Event renderItem.

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
        // Fetch swimmers synchronously (mock DB is sync)
        // passing refreshTrigger in dependency array of useEffect would be better for real async,
        // but here we just re-call the getter on render which is fine for this mock.
        const swimmers = getSwimmersByHeat(heat.id);

        return (
            <View key={heat.id} style={styles.heatContainer}>
                <Text style={styles.heatHeader}>Heat {heat.number}</Text>
                {swimmers.map(swimmer => renderSwimmer(swimmer, event, heat))}
            </View>
        );
    };

    const renderEvent = ({ item }: { item: any }) => {
        const heats = getHeatsByEvent(item.id);
        return (
            <View style={styles.eventContainer}>
                <View style={styles.eventHeader}>
                    <Text style={styles.eventTitle}>
                        #{item.number} {item.name}
                    </Text>
                </View>
                {heats.map(heat => renderHeat(heat, item))}
            </View>
        );
    };

    return (
        <View style={styles.container}>
            <FlatList
                data={events}
                keyExtractor={(item) => item.id.toString()}
                renderItem={renderEvent}
                initialNumToRender={3}
                maxToRenderPerBatch={5}
                windowSize={5}
                extraData={refreshTrigger} // Important: re-render list when trigger changes
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
    },
    eventTitle: {
        color: COLORS.white,
        fontSize: 24, // Tablet friendly
        fontWeight: 'bold',
    },
    heatContainer: {
        paddingBottom: 10,
    },
    heatHeader: {
        backgroundColor: COLORS.heatHeader,
        padding: 10,
        fontSize: 20,
        fontWeight: 'bold',
        color: COLORS.text,
    },
    swimmerRow: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 15, // Large touch target
        borderBottomWidth: 1,
        borderBottomColor: COLORS.lightGray,
    },
    laneContainer: {
        width: 60,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: COLORS.secondary,
        borderRadius: 8,
        padding: 5,
        marginRight: 15,
    },
    laneText: {
        color: COLORS.white,
        fontSize: 20,
        fontWeight: 'bold',
    },
    swimmerDetails: {
        flex: 1,
    },
    swimmerName: {
        fontSize: 22, // Large for readability
        fontWeight: 'bold',
        color: COLORS.text,
    },
    teamName: {
        fontSize: 18,
        color: COLORS.secondary,
    },
    dqContainer: {
        width: 80,
        alignItems: 'center',
        justifyContent: 'center',
        borderLeftWidth: 1,
        borderLeftColor: COLORS.lightGray,
        paddingLeft: 10,
    },
    dqText: {
        color: COLORS.accent,
        fontSize: 24,
        fontWeight: '900',
    },
    dqPlaceholder: {
        color: '#CCC',
        fontSize: 18,
        fontWeight: 'bold',
    }
});
