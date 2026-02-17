import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Text, View, FlatList, TouchableOpacity, Modal, SafeAreaView, ScrollView, ActivityIndicator, TextInput } from 'react-native';
import { initDatabase, seedData, getEvents, getHeatsByEvent, getSwimmersByHeat, saveDQ, getPendingDQs } from './src/database/db';
import defaultDqCodes from './src/config/dqCodes.json';
import { loadDataFromUrl } from './src/services/dataLoader';
import { initSyncService, setSyncEndpoint, triggerSync } from './src/services/syncService';
import { ProgramView } from './src/components/ProgramView';
import type { Event, Heat, Swimmer, DQ, DqCode } from './src/types';

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

const getStrokeForEvent = (event: Event, leg?: number) => {
  if (!event) return null;
  if (event.isRelay && leg) {
    if (event.stroke === 'Medley Relay' || event.name.includes('Medley')) {
      switch (leg) {
        case 1: return 'Back';
        case 2: return 'Breast';
        case 3: return 'Fly';
        case 4: return 'Free';
      }
    }
    return 'Free'; // Free Relay
  }
  return event.stroke || 'Free';
};

const getOrderedDQCategories = (currentStroke: string | null, dqCodes: {[key: string]: DqCode[]}) => {
  const categories = Object.keys(dqCodes);
  if (!currentStroke) return categories;

  const priorityMap: { [key: string]: string } = {
    'Fly': 'butterfly',
    'Back': 'backstroke',
    'Breast': 'breaststroke'
  };

  const targetCategory = priorityMap[currentStroke];

  if (targetCategory) {
    return [
      targetCategory,
      ...categories.filter(c => c !== targetCategory)
    ];
  }
  return categories;
};

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<'events' | 'heats' | 'judge' | 'program'>('events');
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [selectedHeat, setSelectedHeat] = useState<Heat | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [heats, setHeats] = useState<Heat[]>([]);
  const [swimmers, setSwimmers] = useState<Swimmer[]>([]);
  const [dqModalVisible, setDqModalVisible] = useState(false);
  const [selectedSwimmer, setSelectedSwimmer] = useState<Swimmer | null>(null);
  const [selectedLeg, setSelectedLeg] = useState<number | undefined>(undefined);
  const [dqNote, setDqNote] = useState('');
  const [pendingCount, setPendingCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [dqCodes, setDqCodes] = useState<{[key: string]: DqCode[]}>(defaultDqCodes);
  const [programMode, setProgramMode] = useState(false); // Toggle state

  const refreshEvents = useCallback(() => {
    const evts = getEvents();
    setEvents(evts);
  }, []);

  const updatePendingCount = useCallback(() => {
    const pending = getPendingDQs();
    setPendingCount(pending.length);
  }, []);

  useEffect(() => {
    const initializeApp = async () => {
      initDatabase();
      
      const { loaded, dqData, syncUrl } = await loadDataFromUrl();
      
      if (dqData) {
        setDqCodes(dqData);
      }
      
      if (syncUrl) {
        setSyncEndpoint(syncUrl);
      }

      // Initialize sync listener
      initSyncService(updatePendingCount);
      
      if (!loaded) {
        seedData();
      }
      
      refreshEvents();
      updatePendingCount();
      setIsLoading(false);
    };

    initializeApp();
  }, [refreshEvents, updatePendingCount]);

  const selectEvent = (event: Event) => {
    setSelectedEvent(event);
    const hts = getHeatsByEvent(event.id);
    setHeats(hts);
    setCurrentScreen('heats');
  };

  const selectHeat = (heat: Heat) => {
    setSelectedHeat(heat);
    const swmrs = getSwimmersByHeat(heat.id);
    setSwimmers(swmrs);
    setCurrentScreen('judge');
  };

  const handleDQ = (swimmer: Swimmer, leg?: number) => {
    setSelectedSwimmer(swimmer);
    setSelectedLeg(leg);

    // Find existing note
    let existingNote = '';
    if (leg) {
      existingNote = swimmer.relay_dqs?.find((d: DQ) => d.leg === leg)?.notes || '';
    } else {
      existingNote = swimmer.notes || '';
    }

    setDqNote(existingNote);
    setDqModalVisible(true);
  };

  const submitDQ = (code: string) => {
    if (!selectedSwimmer) return;
    saveDQ(selectedEvent ? selectedEvent.id : 0, selectedSwimmer.id, code, selectedLeg, dqNote);
    setDqModalVisible(false);
    updatePendingCount();
    triggerSync(); // Try to sync immediately
    // In a real app, we'd highlight the swimmer as DQ'd
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

  const renderEventItem = ({ item }: { item: Event }) => (
    <TouchableOpacity style={styles.listItem} onPress={() => selectEvent(item)}>
      <Text style={styles.eventNumber}>Event {item.number}</Text>
      <Text style={styles.eventTitle}>{item.name}</Text>
    </TouchableOpacity>
  );

  const renderHeatItem = ({ item }: { item: Heat }) => (
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
                  <Text style={[styles.swimmerName, item.empty && styles.emptyText]}>
                    {item.isRelay ? `Team ${item.team}` : item.name}
                  </Text>
                  {!item.isRelay && <Text style={styles.teamName}>{item.team}</Text>}

                  {!item.empty && (
                    <View style={styles.legsContainer}>
                      {[1, 2, 3, 4].map(leg => {
                        const dq = item.relay_dqs?.find((d: DQ) => d.leg === leg);
                        const legName = item.members?.[leg - 1] ? item.members[leg - 1] : `Leg ${leg}`;
                        return (
                          <TouchableOpacity
                            key={leg}
                            style={styles.legRow}
                            onPress={() => handleDQ(item, leg)}
                          >
                            <View style={{ flex: 1 }}>
                              <Text style={styles.legLabel}>{legName}</Text>
                              {dq?.notes ? (
                                <Text style={styles.notePreview} numberOfLines={1}>
                                  {dq.notes}
                                </Text>
                              ) : null}
                            </View>
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
                {item.notes ? (
                  <Text style={styles.notePreview} numberOfLines={1}>
                    {item.notes}
                  </Text>
                ) : null}
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

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator testID="loading-indicator" size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>Loading Data...</Text>
      </View>
    );
  }

  const currentStroke = selectedEvent ? getStrokeForEvent(selectedEvent, selectedLeg) : null;
  const orderedDQCategories = getOrderedDQCategories(currentStroke, dqCodes);

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
          onSelectSwimmer={(swimmer, event, heat, leg) => {
            setSelectedEvent(event);
            setSelectedHeat(heat);
            handleDQ(swimmer, leg);
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
                DQ: {selectedLeg !== undefined && selectedSwimmer?.members?.[selectedLeg - 1]
                  ? selectedSwimmer.members[selectedLeg - 1]
                  : `${selectedSwimmer?.name || 'Swimmer'}${selectedLeg ? ` - Leg ${selectedLeg}` : ''}`}
              </Text>
              <TouchableOpacity onPress={() => setDqModalVisible(false)}>
                <Text style={styles.closeButton}>CANCEL</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.noteContainer}>
              <TextInput
                style={styles.noteInput}
                placeholder="Add notes here (optional)"
                value={dqNote}
                onChangeText={setDqNote}
                multiline
              />
            </View>
            <ScrollView>
              {orderedDQCategories.map((category) => (
                <View key={category} style={styles.dqCategory}>
                  <Text style={styles.categoryTitle}>{category.toUpperCase()}</Text>
                  {dqCodes[category as keyof typeof dqCodes].map((item: DqCode) => (
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 18,
    color: COLORS.primary,
  },
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
  notePreview: {
    fontSize: 10,
    color: COLORS.secondary,
    fontStyle: 'italic',
    marginTop: 2,
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
  noteContainer: {
    padding: 10,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
  },
  noteInput: {
    borderWidth: 1,
    borderColor: COLORS.secondary,
    borderRadius: 5,
    padding: 10,
    minHeight: 60,
    textAlignVertical: 'top',
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
    paddingLeft: 10,
    borderLeftWidth: 3,
    borderLeftColor: COLORS.accent,
    backgroundColor: '#FAFAFA',
    borderRadius: 4,
  },
  legRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
    paddingRight: 10,
  },
  legLabel: {
    fontWeight: 'bold',
    fontSize: 14,
    color: COLORS.text,
  }
});
