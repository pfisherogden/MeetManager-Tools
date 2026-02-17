import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View, FlatList, TouchableOpacity, Modal, SafeAreaView, ScrollView, TextInput, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
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

const getStrokeForEvent = (event: any, leg?: number) => {
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

const getOrderedDQCategories = (currentStroke: string | null) => {
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

const BUILD_TIME = "2026-02-17 07:00:00 PM"; // Fixed build time

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
  const [dqNote, setDqNote] = useState('');
  const [pendingDqCode, setPendingDqCode] = useState<string[]>([]); // Issue #84: Multi-select
  const [pendingCount, setPendingCount] = useState(0);
  const [offlineModalVisible, setOfflineModalVisible] = useState(false); // Issue #83
  const [programMode, setProgramMode] = useState(false); // Toggle state
  const [refreshCounter, setRefreshCounter] = useState<number>(0);

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

    // Find existing note and code
    let existingNote = '';
    let existingCode: string | null = null;
    if (leg) {
      const dq = swimmer.relay_dqs?.find((d: any) => d.leg === leg);
      existingNote = dq?.notes || '';
      existingCode = dq?.dq_code || null;
    } else {
      existingNote = swimmer.notes || '';
      existingCode = swimmer.dq_code || null;
    }

    setDqNote(existingNote);
    setPendingDqCode(existingCode ? (existingCode as string).split(',') : []); // Issue #84
    setDqModalVisible(true);
  };

  const onSave = () => {
    if (pendingDqCode.length > 0) {
      saveDQ(selectedEvent ? selectedEvent.id : 0, selectedSwimmer.id, pendingDqCode.join(','), selectedLeg, dqNote);
      setDqModalVisible(false);
      updatePendingCount();

      if (selectedHeat) {
        setSwimmers(getSwimmersByHeat(selectedHeat.id));
      }
      setRefreshCounter(prev => prev + 1);
    }
  };

  const onDelete = () => {
    saveDQ(selectedEvent ? selectedEvent.id : 0, selectedSwimmer.id, null as any, selectedLeg, '');
    setDqModalVisible(false);
    updatePendingCount();

    // Refresh swimmers list
    if (selectedHeat) {
      setSwimmers(getSwimmersByHeat(selectedHeat.id));
    }
    setRefreshCounter(prev => prev + 1);
  };

  const onCancel = () => {
    setDqModalVisible(false);
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
            if (item.empty) return null; // Issue #81: Hide empty lanes for relays
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
                        const dq = item.relay_dqs?.find((d: any) => d.leg === leg);
                        const legName = item.members && item.members[leg - 1] ? item.members[leg - 1] : `Leg ${leg}`;
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
                            <Text style={[styles.dqTrigger, !dq && { color: COLORS.secondary }]}>
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
              onPress={() => handleDQ(item)}
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
              <Text style={[styles.dqTrigger, !item.dq_code && { color: COLORS.secondary }]}>
                {item.dq_code ? item.dq_code : 'TAP TO DQ'}
              </Text>
            </TouchableOpacity>
          );
        }}
      />
      {/* Existing Program View needs update? ProgramView uses rendering logic inside itself, might need update too if I want relays there. But Issue #60 usually implies main Judge View. */}
    </View>
  );

  const currentStroke = getStrokeForEvent(selectedEvent, selectedLeg);
  const orderedDQCategories = getOrderedDQCategories(currentStroke);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.statusBar}>
        <Text style={styles.versionText}>v1.0.4</Text>
        <TouchableOpacity onPress={() => setOfflineModalVisible(true)}>
          <Text style={styles.statusText}>Offline Queue: {pendingCount}</Text>
        </TouchableOpacity>
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
          refreshTrigger={refreshCounter}
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
              <View style={styles.headerActions}>
                <TouchableOpacity
                  onPress={onDelete}
                  style={styles.headerIconButton}
                  // @ts-ignore - title is supported on web for tooltips
                  title="Delete DQ and notes"
                  accessibilityLabel="Delete DQ and notes"
                >
                  <Ionicons name="trash-outline" size={24} color={COLORS.accent} />
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={onSave}
                  style={styles.headerIconButton}
                  // @ts-ignore - title is supported on web for tooltips
                  title="Save changes"
                  accessibilityLabel="Save changes"
                >
                  <Ionicons name="save-outline" size={24} color={COLORS.success} />
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={onCancel}
                  style={styles.headerIconButton}
                  // @ts-ignore - title is supported on web for tooltips
                  title="Cancel changes"
                  accessibilityLabel="Cancel changes"
                >
                  <Ionicons name="close-outline" size={24} color={COLORS.secondary} />
                </TouchableOpacity>
              </View>
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
                  {dqCodes[category as keyof typeof dqCodes].map((item: any) => {
                    const isSelected = pendingDqCode.includes(item.code);
                    return (
                      <TouchableOpacity
                        key={item.code}
                        style={[styles.dqItem, isSelected && styles.selectedDqItem]}
                        onPress={() => {
                          if (isSelected) {
                            setPendingDqCode(prev => prev.filter(c => c !== item.code));
                          } else {
                            setPendingDqCode(prev => [...prev, item.code]);
                          }
                        }}
                      >
                        <Text style={[styles.dqCode, isSelected && styles.selectedDqText]}>{item.code}</Text>
                        <Text style={[styles.dqDescription, isSelected && styles.selectedDqText]}>{item.description}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
      {/* Build Timestamp */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>Build: {BUILD_TIME}</Text>
      </View>

      {/* Offline Queue Modal */}
      <Modal visible={offlineModalVisible} animationType="fade" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContainer, styles.offlineModal]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Offline Queue ({pendingCount})</Text>
              <TouchableOpacity onPress={() => setOfflineModalVisible(false)}>
                <Ionicons name="close" size={24} color={COLORS.accent} />
              </TouchableOpacity>
            </View>
            <ScrollView style={{ padding: 15 }}>
              {getPendingDQs().length === 0 ? (
                <Text style={styles.emptyText}>No pending DQs</Text>
              ) : (
                getPendingDQs().map((dq, idx) => (
                  <View key={idx} style={styles.pendingItem}>
                    <Text style={styles.pendingText}>
                      Event {dq.eventId} - Swimmer {dq.swimmerId}
                    </Text>
                    <Text style={styles.pendingCodes}>{dq.dqCode}</Text>
                  </View>
                ))
              )}
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
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerIconButton: {
    marginLeft: 15,
    padding: 5,
  },
  actionIcon: {
    width: 24,
    height: 24,
    resizeMode: 'contain',
  },
  selectedDqItem: {
    backgroundColor: COLORS.primary,
  },
  selectedDqText: {
    color: COLORS.white,
  },
  versionText: {
    position: 'absolute',
    left: 10,
    top: 2,
    fontSize: 8,
    color: '#333333', // Subtle gray on black background
  },
  footer: {
    padding: 5,
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#EEEEEE',
  },
  footerText: {
    fontSize: 10,
    color: COLORS.secondary,
  },
  offlineModal: {
    borderRadius: 15,
    maxHeight: '60%',
    width: '90%',
    alignSelf: 'center',
  },
  pendingItem: {
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
  },
  pendingText: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  pendingCodes: {
    fontSize: 12,
    color: COLORS.accent,
    marginTop: 2,
    fontWeight: 'bold',
  }
});
