import { ProgramView } from './src/components/ProgramView';

// ... (existing imports)

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<'events' | 'heats' | 'judge' | 'program'>('events');
  // ... (existing state)
  const [programMode, setProgramMode] = useState(false); // Toggle state

  // ... (existing helper functions)

  // Toggle Handler
  const toggleViewMode = () => {
    const newMode = !programMode;
    setProgramMode(newMode);
    setCurrentScreen(newMode ? 'program' : 'events');
  };

  // ... (existing render functions)

  return (
    <View style={styles.safeArea}>
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
            handleDQ(swimmer);
          }}
          refreshTrigger={pendingCount} // Re-render when DQs change
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
            <Text style={styles.headerTitle}>Event {selectedEvent.number}</Text>
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
              <Text style={styles.modalTitle}>DQ Swimmer: {selectedSwimmer?.name}</Text>
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
    </View>
  );
}

const styles = StyleSheet.create({
  // ... (existing styles)
  viewToggle: {
    marginTop: 10,
    backgroundColor: COLORS.white,
    padding: 8,
    borderRadius: 20,
  },
  toggleText: {
    color: COLORS.primary,
    fontWeight: 'bold',
    fontSize: 12,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)', // Dim background
    justifyContent: 'center',
    padding: 20,
  },
  modalPopup: {
    borderRadius: 10,
    maxHeight: '80%', // Pop-up style
  }
});
