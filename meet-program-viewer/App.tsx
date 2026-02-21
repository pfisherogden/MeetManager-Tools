import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View, ActivityIndicator, SafeAreaView } from 'react-native';
import { ProgramList } from './src/components/ProgramList';
import { useMeetData } from './src/hooks/useMeetData';
import { COLORS } from './src/constants/colors';

export default function App() {
    const { events, isResults, loading } = useMeetData();

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={COLORS.primary} />
                <Text style={styles.loadingText}>Loading Meet Program...</Text>
            </View>
        );
    }

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar style="auto" />
            <View style={styles.header}>
                <Text style={styles.headerTitle}>
                    {isResults ? 'Meet Results Viewer' : 'Meet Program Viewer'}
                </Text>
            </View>
            <ProgramList events={events} />
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: COLORS.background,
    },
    header: {
        backgroundColor: COLORS.appHeader,
        padding: 15,
        alignItems: 'center',
    },
    headerTitle: {
        color: COLORS.white,
        fontSize: 20,
        fontWeight: 'bold',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: COLORS.background,
    },
    loadingText: {
        marginTop: 10,
        fontSize: 16,
        color: COLORS.secondary,
    },
});
