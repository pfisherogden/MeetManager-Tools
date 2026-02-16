import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View, FlatList, TouchableOpacity, Modal, SafeAreaView, ScrollView } from 'react-native';
import { initDatabase, seedData, getEvents, getHeatsByEvent, getSwimmersByHeat, saveDQ, getPendingDQs } from './src/database/db';
import dqCodes from './src/config/dqCodes.json';
import { ProgramView } from './src/components/ProgramView';

// Simple high-contrast theme
const COLORS = {
  background: '#FFFFFF',
  text: '#000000',
  primary: '#000000',
  secondary: '#555555',
  accent: '#E63946',
  white: '#FFFFFF',
  lightGray: '#F0F0F0',
  success: '#2A9D8F'
};

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<'events' | 'heats' | 'judge' | 'program'>('events');
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [selectedHeat, setSelectedHeat] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [heats, setHeats] = useState<any[]>([]);
  const [swimmers, setSwimmers] = useState<any[]>([]);
  const [dqModalVisible, setDqModalVisible] = useState(false);
  const [selectedSwimmer, setSelectedSwimmer] = useState<any>(null);
  const [selectedLeg, setSelectedLeg] = useState<number | undefined>(undefined);
  const [pendingCount, setPendingCount] = useState(0);
  const [programMode, setProgramMode] = useState(false); // Toggle state

  useEffect(() => {
    initDatabase();
    seedData();
    refreshEvents();
    updatePendingCount();
  }, []);

  const refreshEvents = () => {
    const evts = getEvents();
    setEvents(evts);
  };

  const updatePendingCount = () => {
    const pending = getPendingDQs();
    setPendingCount(pending.length);
  };

  const selectEvent = (event: any) => {
    setSelectedEvent(event);
    const hts = getHeatsByEvent(event.id);
    setHeats(hts);
    setCurrentScreen('heats');
  };

  const selectHeat = (heat: any) => {
    setSelectedHeat(heat);
    const swmrs = getSwimmersByHeat(heat.id);
    setSwimmers(swmrs);
    setCurrentScreen('judge');
  };

  const handleDQ = (swimmer: any, leg?: number) => {
    setSelectedSwimmer(swimmer);
    setSelectedLeg(leg);
    setDqModalVisible(true);
  };

  const submitDQ = (code: string) => {
    saveDQ(selectedEvent ? selectedEvent.id : 0, selectedSwimmer.id, code, selectedLeg);
    setDqModalVisible(false);
    updatePendingCount();

    // Refresh swimmers list to show new DQ
    if (selectedHeat) {
      const updatedSwimmers = getSwimmersByHeat(selectedHeat.id);
      setSwimmers(updatedSwimmers);
    }
  };

  // Toggle Handler
  const toggleViewMode = () => {
    const newMode = !programMode;
    setProgramMode(newMode);
    setCurrentScreen(newMode ? 'program' : 'events');
  };

  const renderEventItem = ({ item }: { item: any }) => (
    <TouchableOpacity style={styles.listItem} onPress={() => selectEvent(item)}>
      <Text style={styles.eventNumber}>Event {item.number}</Text>
      <Text style={styles.eventTitle}>{item.name}</Text>
    </TouchableOpacity>
  );

  const renderHeatItem = ({ item }: { item: any }) => (
    <TouchableOpacity style={styles.listItem} onPress={() => selectHeat(item)}>
      <Text style={styles.title}>Heat {item.number}</Text>
    </TouchableOpacity>
  );

  const renderJudgeView = () => (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setCurrentScreen('heats')}>
          <Text style={styles.backButton}>BACK</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Event {selectedEvent?.number} - Heat {selectedHeat?.number}</Text>
      </View>
      <FlatList
        data={swimmers}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => {
          if (item.isRelay) {
            return (
              <View style={[styles.swimmerCard, styles.relayCard, item.empty && styles.emptyCard]}>
                <View style={[styles.laneCircle, item.empty && styles.emptyLane]}>
                  <Text style={styles.laneText}>{item.lane}</Text>
                </View>
                <View style={styles.swimmerInfo}>
                  <Text style={[styles.swimmerName, item.empty && styles.emptyText]}>{item.name}</Text>
                  <Text style={styles.teamName}>{item.team}</Text>

                  {!item.empty && (
                    <View style={styles.legsContainer}>
                      {[1, 2, 3, 4].map(leg => {
                        const dq = item.relay_dqs?.find((d: any) => d.leg === leg);
                        return (
                          <TouchableOpacity
                            key={leg}
                            style={styles.legRow}
                            onPress={() => handleDQ(item, leg)}
                          >
                            <Text style={styles.legLabel}>Leg {leg}</Text>
                            <Text style={styles.dqTrigger}>
                              {dq ? dq.dq_code : 'TAP TO DQ'}
                            </Text>
                          </TouchableOpacity>
                        );
                      })}
                    </View>
                  )}
                </View>
              </View>
            );
          }

          return (
            <TouchableOpacity
              style={[styles.swimmerCard, item.empty && styles.emptyCard]}
              onPress={() => !item.empty && handleDQ(item)}
              disabled={item.empty}
            >
              <View style={[styles.laneCircle, item.empty && styles.emptyLane]}>
                <Text style={styles.laneText}>{item.lane}</Text>
              </View>
              <View style={styles.swimmerInfo}>
                <Text style={[styles.swimmerName, item.empty && styles.emptyText]}>{item.name}</Text>
                <Text style={styles.teamName}>{item.team}</Text>
              </View>
              {!item.empty && (
                <Text style={styles.dqTrigger}>{item.dq_code ? item.dq_code : 'TAP TO DQ'}</Text>
              )}
            </TouchableOpacity>
          );
        }}
      />
      {/* Existing Program View needs update? ProgramView uses rendering logic inside itself, might need update too if I want relays there. But Issue #60 usually implies main Judge View. */}
    </View>
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.statusBar}>
        <Text style={styles.statusText}>Offline Queue: {pendingCount}</Text>
        <TouchableOpacity onPress={toggleViewMode} style={styles.viewToggle}>
          <Text style={styles.toggleText}>
            {programMode ? 'SWITCH TO EVENT VIEW' : 'SWITCH TO PROGRAM VIEW'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Render Program View */}
      {currentScreen === 'program' && (
        <ProgramView
          events={events}
          onSelectSwimmer={(swimmer, event, heat) => {
            setSelectedEvent(event);
            setSelectedHeat(heat);
            // Program View might need leg support too. For now, assume it's basic.
            handleDQ(swimmer);
          }}
          refreshTrigger={pendingCount}
        />
      )}

      {/* Existing Views (Conditional) */}
      {!programMode && currentScreen === 'events' && (
        <View style={styles.container}>
          <Text style={styles.mainTitle}>Events</Text>
          {events.length === 0 ? (
            <Text>No events loaded. Check database/mock.</Text>
          ) : (
            <FlatList
              data={events}
              keyExtractor={(item) => item.id.toString()}
              renderItem={renderEventItem}
            />
          )}
        </View>
      )}

      {!programMode && currentScreen === 'heats' && (
        <View style={styles.container}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => setCurrentScreen('events')}>
              <Text style={styles.backButton}>EVENTS</Text>
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Event {selectedEvent?.number}</Text>
          </View>
          <FlatList
            data={heats}
            keyExtractor={(item) => item.id.toString()}
            renderItem={renderHeatItem}
          />
        </View>
      )}

      {!programMode && currentScreen === 'judge' && renderJudgeView()}

      <Modal visible={dqModalVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContainer, styles.modalPopup]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                DQ: {selectedSwimmer?.name} {selectedLeg ? `(Leg ${selectedLeg})` : ''}
              </Text>
              <TouchableOpacity onPress={() => setDqModalVisible(false)}>
                <Text style={styles.closeButton}>CANCEL</Text>
              </TouchableOpacity>
            </View>
            <ScrollView>
              {Object.entries(dqCodes).map(([category, codes]) => (
                <View key={category} style={styles.dqCategory}>
                  <Text style={styles.categoryTitle}>{category.toUpperCase()}</Text>
                  {codes.map((item: any) => (
                    <TouchableOpacity
                      key={item.code}
                      style={styles.dqItem}
                      onPress={() => submitDQ(item.code)}
                    >
                      <Text style={styles.dqCode}>{item.code}</Text>
                      <Text style={styles.dqDescription}>{item.description}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  statusBar: {
    backgroundColor: COLORS.primary,
    padding: 10,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statusText: {
    color: COLORS.white,
    fontWeight: 'bold',
  },
  viewToggle: {
    backgroundColor: COLORS.white,
    padding: 8,
    borderRadius: 20,
  },
  toggleText: {
    color: COLORS.primary,
    fontWeight: 'bold',
    fontSize: 12,
  },
  container: {
    flex: 1,
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 15,
  },
  mainTitle: {
    fontSize: 32,
    fontWeight: '900',
    marginBottom: 20,
    color: COLORS.text,
  },
  backButton: {
    fontWeight: 'bold',
    fontSize: 14,
    color: COLORS.accent,
    borderWidth: 1,
    borderColor: COLORS.accent,
    padding: 5,
    borderRadius: 4,
  },
  listItem: {
    padding: 20,
    borderBottomWidth: 2,
    borderBottomColor: COLORS.lightGray,
  },
  eventNumber: {
    fontSize: 14,
    fontWeight: 'bold',
    color: COLORS.secondary,
  },
  eventTitle: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  swimmerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
    backgroundColor: COLORS.lightGray,
    marginBottom: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.primary,
  },
  laneCircle: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  laneText: {
    color: COLORS.white,
    fontSize: 24,
    fontWeight: 'bold',
  },
  swimmerInfo: {
    flex: 1,
    marginLeft: 15,
  },
  swimmerName: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  teamName: {
    fontSize: 14,
    color: COLORS.secondary,
  },
  dqTrigger: {
    color: COLORS.accent,
    fontWeight: '900',
    fontSize: 12,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: 20,
  },
  modalContainer: {
    backgroundColor: COLORS.background,
  },
  modalPopup: {
    borderRadius: 10,
    maxHeight: '80%',
  },
  modalHeader: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    flex: 1,
  },
  closeButton: {
    color: COLORS.accent,
    fontWeight: 'bold',
  },
  dqCategory: {
    padding: 10,
  },
  categoryTitle: {
    backgroundColor: COLORS.primary,
    color: COLORS.white,
    padding: 8,
    fontWeight: 'bold',
    fontSize: 16,
  },
  dqItem: {
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
    flexDirection: 'row',
    alignItems: 'center',
  },
  dqCode: {
    fontSize: 24,
    fontWeight: '900',
    width: 60,
  },
  dqDescription: {
    flex: 1,
    fontSize: 16,
  },
  emptyCard: {
    backgroundColor: '#FAFAFA',
    borderColor: '#E0E0E0',
  },
  emptyLane: {
    backgroundColor: '#CCCCCC',
  },
  emptyText: {
    color: '#999999',
    fontStyle: 'italic',
  },
  relayCard: {
    alignItems: 'flex-start',
  },
  legsContainer: {
    marginTop: 10,
    width: '100%',
  },
  legRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    width: 200, // Or flex
  },
  legLabel: {
    fontWeight: 'bold',
    marginRight: 10,
  }
});
