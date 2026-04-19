import { Ionicons } from "@expo/vector-icons";
import { useCallback, useEffect, useState } from "react";
import {
	ActivityIndicator,
	FlatList,
	Modal,
	Platform,
	SafeAreaView,
	ScrollView,
	StyleSheet,
	Text,
	TextInput,
	TouchableOpacity,
	View,
	TouchableWithoutFeedback,
} from "react-native";
import { ProgramView } from "./src/components/ProgramView";
import defaultDqCodes from "./src/config/dqCodes.json";
import {
	clearAllDQs,
	deleteDQ,
	getAllDQs,
	getEvents,
	getHeatsByEvent,
	getPendingDQs,
	getSwimmerById,
	getSwimmersByHeat,
	initDatabase,
	saveDQ,
	seedData,
} from "./src/database/db";
import { loadDataFromUrl } from "./src/services/dataLoader";
import {
	initSyncService,
	setSyncEndpoint,
	triggerSync,
} from "./src/services/syncService";
import type { DQ, DqCode, Event, Heat, Swimmer } from "./src/types";

// Simple high-contrast theme
const COLORS = {
	background: "#FFFFFF",
	text: "#000000",
	primary: "#000000",
	secondary: "#555555",
	accent: "#E63946",
	white: "#FFFFFF",
	lightGray: "#F0F0F0",
	success: "#2A9D8F",
	danger: "#E63946",
	appHeader: "#1E3A8A",
};

const getStrokeForEvent = (event: Event, leg?: number) => {
	if (!event) return null;
	if (event.isRelay && leg) {
		if (event.stroke === "Medley Relay" || event.name.includes("Medley")) {
			switch (leg) {
				case 1:
					return "Back";
				case 2:
					return "Breast";
				case 3:
					return "Fly";
				case 4:
					return "Free";
			}
		}
		return "Free"; // Free Relay
	}

	const stroke = event.stroke || "";
	if (stroke) return stroke;

	// Fallback: Infer from name
	const name = event.name.toLowerCase();
	if (name.includes("butterfly") || name.includes("fly")) return "Fly";
	if (name.includes("backstroke") || name.includes("back")) return "Back";
	if (name.includes("breaststroke") || name.includes("breast")) return "Breast";
	if (name.includes("freestyle") || name.includes("free")) return "Free";
	if (name.includes("individual medley") || name.includes("im")) return "IM";

	return "Free";
};

const getOrderedDQCategories = (
	currentStroke: string | null,
	dqCodes: { [key: string]: DqCode[] },
) => {
	const categories = Object.keys(dqCodes);
	if (!currentStroke) return categories;

	const priorityMap: { [key: string]: string } = {
		fly: "butterfly",
		butterfly: "butterfly",
		back: "backstroke",
		backstroke: "backstroke",
		breast: "breaststroke",
		breaststroke: "breaststroke",
		free: "freestyle",
		freestyle: "freestyle",
		im: "im",
		"individual medley": "im",
	};

	const targetCategory = priorityMap[currentStroke.toLowerCase()];

	if (targetCategory) {
		const ordered = [
			targetCategory,
			...categories.filter(
				(c) => c !== targetCategory && c !== "miscellaneous",
			),
		];
		// Ensure Miscellaneous is always at the end
		if (categories.includes("miscellaneous")) {
			ordered.push("miscellaneous");
		}
		return ordered;
	}

	// Default order: rest, then miscellaneous
	const defaultOrdered = categories.filter((c) => c !== "miscellaneous");
	if (categories.includes("miscellaneous")) {
		defaultOrdered.push("miscellaneous");
	}
	return defaultOrdered;
};

const BUILD_TIME = "03/13/2026, 11:21:13 PM PT"; // Fixed build time

export default function App() {
	const [currentScreen, setCurrentScreen] = useState<
		"events" | "heats" | "judge" | "program"
	>("events");
	const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
	const [selectedHeat, setSelectedHeat] = useState<Heat | null>(null);
	const [events, setEvents] = useState<Event[]>([]);
	const [heats, setHeats] = useState<Heat[]>([]);
	const [swimmers, setSwimmers] = useState<Swimmer[]>([]);
	const [dqModalVisible, setDqModalVisible] = useState(false);
	const [selectedSwimmer, setSelectedSwimmer] = useState<Swimmer | null>(null);
	const [selectedLeg, setSelectedLeg] = useState<number | undefined>(undefined);
	const [dqNote, setDqNote] = useState("");
	const [pendingDqCode, setPendingDqCode] = useState<string[]>([]); // Issue #84: Multi-select
	const [pendingCount, setPendingCount] = useState(0);
	const [allDQs, setAllDQs] = useState<DQ[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [dqCodes, setDqCodes] = useState<{ [key: string]: DqCode[] }>(
		defaultDqCodes,
	);
	const [offlineModalVisible, setOfflineModalVisible] = useState(false); // Issue #83
	const [programMode, setProgramMode] = useState(false); // Toggle state
	const [showEmptyLanes, setShowEmptyLanes] = useState(true); // Issue #140
	const [refreshCounter, setRefreshCounter] = useState<number>(0);
	const [judgeName, setJudgeName] = useState<string>("");
	const [namePromptVisible, setNamePromptVisible] = useState(false);

	const [loadError, setLoadError] = useState<string | null>(null);

	const refreshEvents = useCallback(() => {
		const evts = getEvents();
		setEvents(evts);
		if (selectedHeat) {
			setSwimmers(getSwimmersByHeat(selectedHeat.id));
		}
		setRefreshCounter((prev) => prev + 1);
	}, [selectedHeat]);

	const updatePendingCount = useCallback(() => {
		const pending = getPendingDQs();
		setPendingCount(pending.length);
		setAllDQs(getAllDQs());
	}, []);

	const handleSyncComplete = useCallback(() => {
		updatePendingCount();
		refreshEvents();
	}, [updatePendingCount, refreshEvents]);

	useEffect(() => {
		const initializeApp = async () => {
			console.log("APP: Initializing...");
			try {
				console.log("APP: Calling initDatabase()...");
				initDatabase();
				console.log("APP: initDatabase() done.");

				// 1. Detect dataset change and clear stale DQs if needed
				if (typeof window !== "undefined" && window.localStorage) {
					console.log("APP: Checking localStorage...");
					const currentUrl = window.location.search;
					const lastUrl = window.localStorage.getItem("mmtools_last_url");
					
					// Only clear if the URL (and thus the meet dataset) has actually changed
					if (lastUrl && lastUrl !== currentUrl) {
						console.log("APP: Dataset changed, clearing local DQ history");
						clearAllDQs();
						window.localStorage.removeItem("mmtools_judge_name"); // Reset name on new meet
					}
					window.localStorage.setItem("mmtools_last_url", currentUrl);

					// 2. Load judge name or prompt for it
					const savedName = window.localStorage.getItem("mmtools_judge_name");
					console.log(`APP: Saved name: ${savedName}`);
					if (savedName) {
						setJudgeName(savedName);
					} else {
						console.log("APP: No name found, will show prompt.");
						setNamePromptVisible(true);
					}
				}

				console.log("APP: Calling loadDataFromUrl()...");
				const { loaded, dqData, syncUrl, errorMessage } = await loadDataFromUrl();
				console.log(`APP: loadDataFromUrl() result: loaded=${loaded}, error=${errorMessage}`);

				if (dqData) {
					setDqCodes(dqData);
				}

				if (syncUrl) {
					setSyncEndpoint(syncUrl);
				}

				// Initialize sync listener
				initSyncService(handleSyncComplete);

				if (!loaded) {
					// If error message exists, it means we TRIED to load but failed
					if (errorMessage) {
						console.log(`APP: Load failed: ${errorMessage}`);
						setLoadError(errorMessage);
						setIsLoading(false);
						return;
					}
					console.log("APP: Not loaded from URL, seeding default data...");
					seedData();
				}

				refreshEvents();
				updatePendingCount();
				console.log("APP: Initialization complete, setting isLoading=false");
				setIsLoading(false);
			} catch (err: any) {
				console.error("APP: FATAL INITIALIZATION ERROR:", err);
				setLoadError(`Fatal Init Error: ${err.message}`);
				setIsLoading(false);
			}
		};

		initializeApp();
	}, [refreshEvents, updatePendingCount, handleSyncComplete]);

	const selectEvent = (event: Event) => {
		setSelectedEvent(event);
		const hts = getHeatsByEvent(event.id);
		setHeats(hts);
		setCurrentScreen("heats");
	};

	const selectHeat = (heat: Heat) => {
		setSelectedHeat(heat);
		const swmrs = getSwimmersByHeat(heat.id);
		setSwimmers(swmrs);
		setCurrentScreen("judge");
	};

	const handleDQ = (swimmer: Swimmer, leg?: number) => {
		setSelectedSwimmer(swimmer);
		setSelectedLeg(leg);

		// Find existing note and code
		let existingNote = "";
		let existingCode: string | null = null;
		if (leg) {
			const dq = swimmer.relay_dqs?.find((d: any) => d.leg === leg);
			existingNote = dq?.notes || "";
			existingCode = dq?.dq_code || null;
		} else {
			existingNote = swimmer.notes || "";
			existingCode = swimmer.dq_code || null;
		}

		setDqNote(existingNote);
		setPendingDqCode(existingCode ? (existingCode as string).split(",") : []); // Issue #84
		setDqModalVisible(true);
	};

	const onSave = () => {
		if (!selectedSwimmer) return;
		if (pendingDqCode.length > 0) {
			saveDQ(
				selectedEvent ? selectedEvent.id : 0,
				selectedSwimmer.id,
				pendingDqCode.join(","),
				selectedLeg,
				dqNote,
			);
			setDqModalVisible(false);
			updatePendingCount();
			triggerSync(); // Try to sync immediately
			refreshEvents(); // Sync views
		}
	};

	const handleDeleteDQ = (swimmerId: number | string, leg?: number) => {
		deleteDQ(swimmerId, leg);
		updatePendingCount();
		refreshEvents();
	};

	const handleClearAll = () => {
		clearAllDQs();
		updatePendingCount();
		refreshEvents();
	};

	const handleEditDQ = (dq: DQ) => {
		// 1. Close offline modal
		setOfflineModalVisible(false);

		// 2. Find the swimmer object using the new helper
		const evt = events.find((e) => e.id === dq.event_id);
		if (evt) {
			setSelectedEvent(evt);
			const swimmer = getSwimmerById(dq.swimmer_id);
			if (swimmer) {
				setSelectedSwimmer(swimmer);
				setSelectedLeg(dq.leg);
				setDqNote(dq.notes || "");
				setPendingDqCode(dq.dq_code ? dq.dq_code.split(",") : []);
				setDqModalVisible(true);
			}
		}
	};

	const onDelete = () => {
		if (!selectedSwimmer) return;
		deleteDQ(selectedSwimmer.id, selectedLeg);
		setDqModalVisible(false);
		updatePendingCount();
		refreshEvents(); // This will refresh swimmers and counter
	};

	const _onCancel = () => {
		setDqModalVisible(false);
	};

	const loadDQState = (swimmer: Swimmer, leg: number | undefined) => {
		let dqObj: any;
		if (leg === undefined) {
			dqObj = swimmer.dq_code
				? { dq_code: swimmer.dq_code, notes: swimmer.notes }
				: null;
		} else {
			dqObj = swimmer.relay_dqs?.find((d: DQ) => d.leg === leg);
		}
		setDqNote(dqObj?.notes || "");
		setPendingDqCode(dqObj?.dq_code ? dqObj.dq_code.split(",") : []);
	};

	const navigateToPrevHeat = (autoSelectFirstSwimmer = false) => {
		const currentHeatIndex = heats.findIndex((h) => h.id === selectedHeat?.id);
		let targetEvent = selectedEvent;
		let targetHeat = null;

		if (currentHeatIndex > 0) {
			targetHeat = heats[currentHeatIndex - 1];
		} else {
			const currentEventIndex = events.findIndex(
				(e) => e.id === selectedEvent?.id,
			);
			if (currentEventIndex > 0) {
				targetEvent = events[currentEventIndex - 1];
				const prevEventHeats = getHeatsByEvent(targetEvent.id);
				if (prevEventHeats.length > 0) {
					targetHeat = prevEventHeats[prevEventHeats.length - 1];
				}
			}
		}

		if (targetHeat && targetEvent) {
			setSelectedEvent(targetEvent);
			setSelectedHeat(targetHeat);
			if (autoSelectFirstSwimmer) {
				const newSwimmers = getSwimmersByHeat(targetHeat.id);
				if (newSwimmers.length > 0) {
					setSelectedSwimmer(newSwimmers[0]);
					setSelectedLeg(undefined);
					loadDQState(newSwimmers[0], undefined);
				} else {
					setDqModalVisible(false);
				}
			}
		}
	};

	const navigateToNextHeat = (autoSelectFirstSwimmer = false) => {
		const currentHeatIndex = heats.findIndex((h) => h.id === selectedHeat?.id);
		let targetEvent = selectedEvent;
		let targetHeat = null;

		if (currentHeatIndex < heats.length - 1) {
			targetHeat = heats[currentHeatIndex + 1];
		} else {
			const currentEventIndex = events.findIndex(
				(e) => e.id === selectedEvent?.id,
			);
			if (currentEventIndex < events.length - 1) {
				targetEvent = events[currentEventIndex + 1];
				const nextEventHeats = getHeatsByEvent(targetEvent.id);
				if (nextEventHeats.length > 0) {
					targetHeat = nextEventHeats[0];
				}
			}
		}

		if (targetHeat && targetEvent) {
			setSelectedEvent(targetEvent);
			setSelectedHeat(targetHeat);
			if (autoSelectFirstSwimmer) {
				const newSwimmers = getSwimmersByHeat(targetHeat.id);
				if (newSwimmers.length > 0) {
					setSelectedSwimmer(newSwimmers[0]);
					setSelectedLeg(undefined);
					loadDQState(newSwimmers[0], undefined);
				} else {
					setDqModalVisible(false);
				}
			}
		}
	};

	const handlePrevSwimmer = () => {
		if (!selectedSwimmer) return;

		if (selectedSwimmer.isRelay) {
			if (selectedLeg === 1) {
				setSelectedLeg(undefined);
				loadDQState(selectedSwimmer, undefined);
				return;
			} else if (selectedLeg !== undefined) {
				setSelectedLeg(selectedLeg - 1);
				loadDQState(selectedSwimmer, selectedLeg - 1);
				return;
			}
		}

		const currentSwimmers = getSwimmersByHeat(selectedHeat?.id || 0);
		const swimmerIndex = currentSwimmers.findIndex(
			(s) => s.id === selectedSwimmer.id,
		);

		if (swimmerIndex > 0) {
			const prevSwimmer = currentSwimmers[swimmerIndex - 1];
			setSelectedSwimmer(prevSwimmer);
			if (prevSwimmer.isRelay) {
				setSelectedLeg(4);
				loadDQState(prevSwimmer, 4);
			} else {
				setSelectedLeg(undefined);
				loadDQState(prevSwimmer, undefined);
			}
		}
	};

	const handleNextSwimmer = () => {
		if (!selectedSwimmer) return;

		if (selectedSwimmer.isRelay) {
			if (selectedLeg === undefined) {
				setSelectedLeg(1);
				loadDQState(selectedSwimmer, 1);
				return;
			} else if (selectedLeg < 4) {
				setSelectedLeg(selectedLeg + 1);
				loadDQState(selectedSwimmer, selectedLeg + 1);
				return;
			}
		}

		const currentSwimmers = getSwimmersByHeat(selectedHeat?.id || 0);
		const swimmerIndex = currentSwimmers.findIndex(
			(s) => s.id === selectedSwimmer.id,
		);

		if (swimmerIndex > -1 && swimmerIndex < currentSwimmers.length - 1) {
			const nextSwimmer = currentSwimmers[swimmerIndex + 1];
			setSelectedSwimmer(nextSwimmer);
			setSelectedLeg(undefined);
			loadDQState(nextSwimmer, undefined);
		}
	};

	// Toggle Handler
	const toggleViewMode = () => {
		const newMode = !programMode;
		setProgramMode(newMode);
		setCurrentScreen(newMode ? "program" : "events");
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
				<TouchableOpacity onPress={() => setCurrentScreen("heats")}>
					<Text style={styles.backButton}>BACK</Text>
				</TouchableOpacity>
				<View
					style={{
						flexDirection: "row",
						alignItems: "center",
						flex: 1,
						justifyContent: "center",
					}}
				>
					<TouchableOpacity
						onPress={() => navigateToPrevHeat(false)}
						style={styles.heatNavButton}
					>
						<Ionicons name="play-skip-back" size={24} color={COLORS.primary} />
					</TouchableOpacity>
					<Text style={styles.headerTitle}>
						Event {selectedEvent?.number} - Heat {selectedHeat?.number}
					</Text>
					<TouchableOpacity
						onPress={() => navigateToNextHeat(false)}
						style={styles.heatNavButton}
					>
						<Ionicons
							name="play-skip-forward"
							size={24}
							color={COLORS.primary}
						/>
					</TouchableOpacity>
				</View>
				<TouchableOpacity
					onPress={() => setShowEmptyLanes(!showEmptyLanes)}
					style={styles.headerIconButton}
				>
					<Ionicons
						name={showEmptyLanes ? "eye" : "eye-off"}
						size={24}
						color={COLORS.primary}
					/>
				</TouchableOpacity>
			</View>
			<FlatList
				data={swimmers}
				keyExtractor={(item) => item.id.toString()}
				renderItem={({ item }) => {
					if (item.empty && !showEmptyLanes) return null;

					if (item.isRelay) {
						return (
							<View
								style={[
									styles.swimmerCard,
									styles.relayCard,
									item.empty && styles.emptyCard,
								]}
							>
								<View
									style={[styles.laneCircle, item.empty && styles.emptyLane]}
								>
									<Text style={styles.laneText}>
										{item.empty ? `(${item.lane})` : item.lane}
									</Text>
								</View>
								<View style={styles.swimmerInfo}>
									<TouchableOpacity
										onPress={() => handleDQ(item)}
										style={{
											flexDirection: "row",
											alignItems: "center",
											justifyContent: "space-between",
										}}
									>
										<Text
											style={[
												styles.swimmerName,
												item.empty && styles.emptyText,
											]}
										>
											{item.isRelay ? `Team ${item.team}` : item.name}
										</Text>
										{item.isRelay && item.dq_code ? (
											<Text
												style={[
													styles.dqTrigger,
													styles.dqSetText,
													{ marginRight: 10 },
												]}
											>
												{item.dq_code}
											</Text>
										) : null}
										{!item.isRelay && (
											<Text style={styles.teamName}>{item.team}</Text>
										)}
									</TouchableOpacity>

									{!item.empty && (
										<View style={styles.legsContainer}>
											{[1, 2, 3, 4].map((leg) => {
												const dq = item.relay_dqs?.find(
													(d: DQ) => d.leg === leg,
												);
												const membersList = item.members || (item as any).relaySwimmers || [];
												const legName = membersList[leg - 1]
													? membersList[leg - 1]
													: `Leg ${leg}`;
												return (

													<TouchableOpacity
														key={leg}
														style={styles.legRow}
														onPress={() => handleDQ(item, leg)}
													>
														<View style={{ flex: 1 }}>
															<Text style={styles.legLabel}>{legName}</Text>
															{dq?.notes ? (
																<Text
																	style={styles.notePreview}
																	numberOfLines={1}
																>
																	{dq.notes}
																</Text>
															) : null}
														</View>
														<Text
															style={[
																styles.dqTrigger,
																!dq && { color: COLORS.secondary },
															]}
														>
															{dq ? dq.dq_code : "TAP TO DQ"}
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

					// Render standard swimmer view
					return (
						<TouchableOpacity
							style={[styles.swimmerCard, item.empty && styles.emptyCard]}
							onPress={() => handleDQ(item)}
						>
							<View style={[styles.laneCircle, item.empty && styles.emptyLane]}>
								<Text style={styles.laneText}>
									{item.empty ? `(${item.lane})` : item.lane}
								</Text>
							</View>
							<View style={styles.swimmerInfo}>
								<Text
									style={[styles.swimmerName, item.empty && styles.emptyText]}
								>
									{item.empty ? "Empty Lane" : item.name}
								</Text>
								<Text style={styles.teamName}>{item.team}</Text>
								{item.notes ? (
									<Text style={styles.notePreview} numberOfLines={1}>
										{item.notes}
									</Text>
								) : null}
							</View>
							<Text
								style={[
									styles.dqTrigger,
									!item.dq_code && { color: COLORS.secondary },
								]}
							>
								{item.dq_code ? item.dq_code : "TAP TO DQ"}
							</Text>
						</TouchableOpacity>
					);
				}}
			/>
		</View>
	);

	if (isLoading) {
		return (
			<View style={styles.loadingContainer}>
				<ActivityIndicator
					testID="loading-indicator"
					size="large"
					color={COLORS.primary}
				/>
				<Text style={styles.loadingText}>Loading Data...</Text>
			</View>
		);
	}

	if (loadError) {
		return (
			<View style={styles.loadingContainer}>
				<Ionicons name="alert-circle" size={64} color={COLORS.danger} />
				<Text
					style={[styles.loadingText, { color: COLORS.danger, marginTop: 20 }]}
				>
					Failed to Load Meet Data
				</Text>
				<Text
					style={{
						textAlign: "center",
						marginHorizontal: 40,
						marginTop: 10,
						color: COLORS.secondary,
					}}
				>
					{loadError}
				</Text>
				<TouchableOpacity
					onPress={() =>
						Platform.OS === "web" ? window.location.reload() : {}
					}
					style={{
						marginTop: 30,
						backgroundColor: COLORS.primary,
						paddingHorizontal: 20,
						paddingVertical: 10,
						borderRadius: 8,
					}}
				>
					<Text style={{ color: COLORS.white, fontWeight: "bold" }}>RETRY</Text>
				</TouchableOpacity>
			</View>
		);
	}

	const currentStroke = selectedEvent
		? getStrokeForEvent(selectedEvent, selectedLeg)
		: null;
	const orderedDQCategories = getOrderedDQCategories(currentStroke, dqCodes);

	return (
		<SafeAreaView style={styles.safeArea}>
			{/* Judge Name Prompt */}
			<Modal visible={namePromptVisible} animationType="fade" transparent={true}>
				<View style={styles.modalOverlay}>
					<View style={[styles.modalContainer, styles.modalPopup, { padding: 25 }]}>
						<Text style={[styles.mainTitle, { fontSize: 24, marginBottom: 10 }]}>Welcome, Judge</Text>
						<Text style={{ marginBottom: 20, color: COLORS.secondary }}>
							Please enter your name to begin. This will be used to identify your DQ submissions.
						</Text>
						<TextInput
							style={[styles.noteInput, { minHeight: 50, fontSize: 18, marginBottom: 20 }]}
							placeholder="Your Name"
							value={judgeName}
							onChangeText={setJudgeName}
							autoFocus
						/>
						<TouchableOpacity 
							onPress={() => {
								if (judgeName.trim()) {
									if (typeof window !== "undefined" && window.localStorage) {
										window.localStorage.setItem("mmtools_judge_name", judgeName.trim());
									}
									setNamePromptVisible(false);
								}
							}}
							style={{ 
								backgroundColor: COLORS.primary, 
								padding: 15, 
								borderRadius: 8,
								alignItems: 'center'
							}}
						>
							<Text style={{ color: COLORS.white, fontWeight: 'bold', fontSize: 16 }}>START JUDGING</Text>
						</TouchableOpacity>
					</View>
				</View>
			</Modal>

			<View style={styles.statusBar}>
				<Text style={styles.versionText}>v1.0.4 ({BUILD_TIME})</Text>
				<TouchableOpacity onPress={() => setOfflineModalVisible(true)}>
					<Text style={styles.statusText}>DQ History (Pending: {pendingCount})</Text>
				</TouchableOpacity>
				<View style={{ flexDirection: "row", alignItems: "center" }}>
					{programMode && (
						<TouchableOpacity
							onPress={() => setShowEmptyLanes(!showEmptyLanes)}
							style={{ marginRight: 15 }}
						>
							<Ionicons
								name={showEmptyLanes ? "eye" : "eye-off"}
								size={24}
								color={COLORS.white}
							/>
						</TouchableOpacity>
					)}
					<TouchableOpacity onPress={toggleViewMode} style={styles.viewToggle}>
						<Text style={styles.toggleText}>
							{programMode ? "SWITCH TO EVENT VIEW" : "SWITCH TO PROGRAM VIEW"}
						</Text>
					</TouchableOpacity>
				</View>
			</View>

			{/* Render Program View */}
			{currentScreen === "program" && (
				<ProgramView
					events={events}
					onSelectSwimmer={(swimmer, event, heat, leg) => {
						setSelectedEvent(event);
						setHeats(getHeatsByEvent(event.id));
						setSelectedHeat(heat);
						setSwimmers(getSwimmersByHeat(heat.id));
						handleDQ(swimmer, leg);
					}}
					refreshTrigger={refreshCounter}
					showEmptyLanes={showEmptyLanes}
				/>
			)}

			{/* Existing Views (Conditional) */}
			{!programMode && currentScreen === "events" && (
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

			{!programMode && currentScreen === "heats" && (
				<View style={styles.container}>
					<View style={styles.header}>
						<TouchableOpacity onPress={() => setCurrentScreen("events")}>
							<Text style={styles.backButton}>EVENTS</Text>
						</TouchableOpacity>
						<Text style={styles.headerTitle}>
							Event {selectedEvent?.number}
						</Text>
					</View>
					<FlatList
						data={heats}
						keyExtractor={(item) => item.id.toString()}
						renderItem={renderHeatItem}
					/>
				</View>
			)}

			{!programMode && currentScreen === "judge" && renderJudgeView()}

			<Modal visible={dqModalVisible} animationType="slide" transparent={true}>
				<TouchableOpacity
					style={styles.modalOverlay}
					activeOpacity={1}
					onPress={() => setDqModalVisible(false)}
				>
					<TouchableOpacity
						style={[styles.modalContainer, styles.modalPopup]}
						activeOpacity={1}
						onPress={(e) => e.stopPropagation()}
					>
						<View style={[styles.modalHeader, { flexDirection: "column" }]}>
							<View
								style={{
									alignItems: "center",
									marginBottom: 15,
									width: "100%",
								}}
							>
								<Text style={{ fontSize: 20, fontWeight: "bold" }}>
									Lane {selectedSwimmer?.lane} • E{selectedEvent?.number} • H
									{selectedHeat?.number}
								</Text>
								<Text
									style={[
										styles.modalTitle,
										{
											textAlign: "center",
											fontSize: 16,
											fontWeight: "normal",
											color: COLORS.secondary,
										},
									]}
									numberOfLines={1}
								>
									{selectedLeg !== undefined &&
									selectedSwimmer?.members?.[selectedLeg - 1]
										? selectedSwimmer.members[selectedLeg - 1]
										: selectedSwimmer?.name || "Swimmer"}
									{selectedLeg ? ` (Leg ${selectedLeg})` : ""}
								</Text>
							</View>

							<View
								style={{
									flexDirection: "row",
									alignItems: "center",
									width: "100%",
									justifyContent: "space-between",
								}}
							>
								<View style={{ flexDirection: "row", alignItems: "center" }}>
									<TouchableOpacity
										onPress={() => navigateToPrevHeat(true)}
										style={{ padding: 5, marginRight: 10 }}
									>
										<Ionicons
											name={
												programMode ? "chevron-up-circle" : "play-skip-back"
											}
											size={32}
											color={COLORS.primary}
										/>
									</TouchableOpacity>
									<TouchableOpacity
										onPress={handlePrevSwimmer}
										style={{ padding: 5 }}
									>
										<Ionicons
											name="chevron-back"
											size={32}
											color={COLORS.primary}
										/>
									</TouchableOpacity>
								</View>

								<View style={styles.headerActions}>
									<TouchableOpacity
										onPress={onSave}
										style={[styles.headerIconButton, { marginLeft: 0 }]}
										accessibilityLabel="Save changes"
									>
										<Ionicons
											name="checkmark-circle"
											size={48}
											color={COLORS.success}
										/>
									</TouchableOpacity>
									<TouchableOpacity
										onPress={onDelete}
										style={styles.headerIconButton}
										accessibilityLabel="Close and delete DQ"
									>
										<Ionicons
											name="close-circle"
											size={48}
											color={COLORS.danger}
										/>
									</TouchableOpacity>
								</View>

								<View style={{ flexDirection: "row", alignItems: "center" }}>
									<TouchableOpacity
										onPress={handleNextSwimmer}
										style={{ padding: 5, marginRight: 10 }}
									>
										<Ionicons
											name="chevron-forward"
											size={32}
											color={COLORS.primary}
										/>
									</TouchableOpacity>
									<TouchableOpacity
										onPress={() => navigateToNextHeat(true)}
										style={{ padding: 5 }}
									>
										<Ionicons
											name={
												programMode
													? "chevron-down-circle"
													: "play-skip-forward"
											}
											size={32}
											color={COLORS.primary}
										/>
									</TouchableOpacity>
								</View>
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
									<Text style={styles.categoryTitle}>
										{category.toUpperCase()}
									</Text>
									{dqCodes[category as keyof typeof dqCodes].map(
										(item: any) => {
											const isSelected = pendingDqCode.includes(item.code);
											return (
												<TouchableOpacity
													key={item.code}
													style={[
														styles.dqItem,
														isSelected && styles.selectedDqItem,
													]}
													onPress={() => {
														if (isSelected) {
															setPendingDqCode((prev) =>
																prev.filter((c) => c !== item.code),
															);
														} else {
															setPendingDqCode((prev) => [...prev, item.code]);
														}
													}}
												>
													<Text
														style={[
															styles.dqCode,
															isSelected && styles.selectedDqText,
														]}
													>
														{item.code}
													</Text>
													<Text
														style={[
															styles.dqDescription,
															isSelected && styles.selectedDqText,
														]}
													>
														{item.description}
													</Text>
												</TouchableOpacity>
											);
										},
									)}
								</View>
							))}
						</ScrollView>
					</TouchableOpacity>
				</TouchableOpacity>
			</Modal>
			{/* Build Timestamp */}
			<View style={styles.footer}>
				<Text style={styles.footerText}>Build: {BUILD_TIME}</Text>
			</View>

			{/* DQ History Modal */}
			<Modal
				visible={offlineModalVisible}
				animationType="slide"
				transparent={true}
				onRequestClose={() => setOfflineModalVisible(false)}
			>
				<TouchableWithoutFeedback
					onPress={() => setOfflineModalVisible(false)}
				>
					<View style={styles.modalOverlay}>
						<TouchableWithoutFeedback onPress={(e) => e.stopPropagation()}>
							<View style={[styles.modalContainer, styles.offlineModal]}>
								<View style={styles.modalHeader}>
									<View style={{ flexDirection: "row", alignItems: "center" }}>
										<Text style={styles.modalTitle}>
											DQ History (Total: {allDQs.length})
										</Text>
									</View>
									{pendingCount > 0 && (
										<TouchableOpacity
											onPress={handleClearAll}
											style={{
												marginLeft: 15,
												padding: 5,
												backgroundColor: `${COLORS.danger}22`,
												borderRadius: 4,
											}}
										>
											<Text
												style={{
													color: COLORS.danger,
													fontWeight: "bold",
													fontSize: 12,
												}}
											>
												CLEAR PENDING
											</Text>
										</TouchableOpacity>
									)}
									<TouchableOpacity
										onPress={() => setOfflineModalVisible(false)}
										accessibilityLabel="Close history"
									>
										<Ionicons name="close" size={24} color={COLORS.accent} />
									</TouchableOpacity>
								</View>
						<ScrollView style={{ padding: 15 }}>
							{allDQs.length === 0 ? (
								<Text style={styles.emptyText}>No DQs recorded</Text>
							) : (
								allDQs.map((dq) => {
									const swimmer = getSwimmerById(dq.swimmer_id);
									const isSynced = dq.sync_status === "synced";
									
									// Correct leg name for relays
									let legInfo = "";
									if (dq.leg) {
										const memberName = swimmer?.members?.[dq.leg - 1];
										legInfo = memberName ? ` (${memberName})` : ` (Leg ${dq.leg})`;
									}

									return (
										<View
											key={`${dq.event_id}-${dq.swimmer_id}-${dq.leg}-${dq.timestamp}`}
											style={styles.pendingCard}
										>
											<TouchableOpacity
												onPress={() => handleDeleteDQ(dq.swimmer_id, dq.leg)}
												style={styles.deletePendingButton}
											>
												<Ionicons
													name="trash-outline"
													size={20}
													color={COLORS.danger}
												/>
											</TouchableOpacity>
											<TouchableOpacity
												style={styles.pendingInfo}
												onPress={() => handleEditDQ(dq)}
											>
												<View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
													<Text style={styles.pendingText}>
														Event {dq.event_id} -{" "}
														{swimmer?.name || `Swimmer ${dq.swimmer_id}`}
														{legInfo}
													</Text>
													<Ionicons 
														name={isSynced ? "cloud-done" : "cloud-offline"} 
														size={18} 
														color={isSynced ? COLORS.success : COLORS.secondary} 
													/>
												</View>
												<Text style={styles.pendingCodes}>{dq.dq_code}</Text>
												{dq.notes ? (
													<Text style={styles.pendingNote} numberOfLines={1}>
														{dq.notes}
													</Text>
												) : null}
											</TouchableOpacity>
										</View>
									);
								})
							)}
						</ScrollView>
					</View>
				</TouchableWithoutFeedback>
			</TouchableWithoutFeedback>
		</Modal>
		</SafeAreaView>
	);
}

const styles = StyleSheet.create({
	loadingContainer: {
		flex: 1,
		justifyContent: "center",
		alignItems: "center",
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
		backgroundColor: COLORS.appHeader,
		padding: 10,
		alignItems: "center",
		flexDirection: "row",
		justifyContent: "space-between",
	},
	statusText: {
		color: COLORS.white,
		fontWeight: "bold",
	},
	viewToggle: {
		backgroundColor: COLORS.white,
		padding: 8,
		borderRadius: 20,
	},
	toggleText: {
		color: COLORS.primary,
		fontWeight: "bold",
		fontSize: 12,
	},
	container: {
		flex: 1,
		padding: 16,
	},
	header: {
		flexDirection: "row",
		alignItems: "center",
		marginBottom: 20,
	},
	headerTitle: {
		fontSize: 18,
		fontWeight: "bold",
		marginLeft: 15,
	},
	mainTitle: {
		fontSize: 32,
		fontWeight: "900",
		marginBottom: 20,
		color: COLORS.text,
	},
	backButton: {
		fontWeight: "bold",
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
		fontWeight: "bold",
		color: COLORS.secondary,
	},
	eventTitle: {
		fontSize: 20,
		fontWeight: "bold",
	},
	title: {
		fontSize: 24,
		fontWeight: "bold",
	},
	swimmerCard: {
		flexDirection: "row",
		alignItems: "center",
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
		justifyContent: "center",
		alignItems: "center",
	},
	laneText: {
		color: COLORS.white,
		fontSize: 24,
		fontWeight: "bold",
	},
	swimmerInfo: {
		flex: 1,
		marginLeft: 15,
	},
	swimmerName: {
		fontSize: 18,
		fontWeight: "bold",
	},
	teamName: {
		fontSize: 14,
		color: COLORS.secondary,
	},
	dqTrigger: {
		color: COLORS.accent,
		fontWeight: "900",
		fontSize: 12,
	},
	dqSetText: {
		color: COLORS.danger,
		fontWeight: "bold",
	},
	notePreview: {
		fontSize: 10,
		color: COLORS.secondary,
		fontStyle: "italic",
		marginTop: 2,
	},
	modalOverlay: {
		flex: 1,
		backgroundColor: "rgba(0,0,0,0.5)",
		justifyContent: "center",
		padding: 20,
	},
	modalContainer: {
		backgroundColor: COLORS.background,
	},
	modalPopup: {
		borderRadius: 10,
		maxHeight: "80%",
	},
	modalHeader: {
		padding: 20,
		borderBottomWidth: 1,
		borderBottomColor: COLORS.lightGray,
		flexDirection: "row",
		justifyContent: "space-between",
		alignItems: "center",
	},
	modalTitle: {
		fontSize: 18,
		fontWeight: "bold",
		flex: 1,
	},
	closeButton: {
		color: COLORS.accent,
		fontWeight: "bold",
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
		textAlignVertical: "top",
	},
	dqCategory: {
		padding: 10,
	},
	categoryTitle: {
		backgroundColor: COLORS.primary,
		color: COLORS.white,
		padding: 8,
		fontWeight: "bold",
		fontSize: 16,
	},
	dqItem: {
		padding: 15,
		borderBottomWidth: 1,
		borderBottomColor: COLORS.lightGray,
		flexDirection: "row",
		alignItems: "center",
	},
	dqCode: {
		fontSize: 24,
		fontWeight: "900",
		width: 60,
	},
	dqDescription: {
		flex: 1,
		fontSize: 16,
	},
	emptyCard: {
		backgroundColor: "#FAFAFA",
		borderColor: "#E0E0E0",
	},
	emptyLane: {
		backgroundColor: "#CCCCCC",
	},
	emptyText: {
		color: "#999999",
		fontStyle: "italic",
	},
	relayCard: {
		alignItems: "flex-start",
	},
	legsContainer: {
		marginTop: 10,
		width: "100%",
		paddingLeft: 10,
		borderLeftWidth: 3,
		borderLeftColor: COLORS.accent,
		backgroundColor: "#FAFAFA",
		borderRadius: 4,
	},
	legRow: {
		flexDirection: "row",
		justifyContent: "space-between",
		paddingVertical: 12,
		borderBottomWidth: 1,
		borderBottomColor: "#EEE",
		paddingRight: 10,
	},
	legLabel: {
		fontWeight: "bold",
		fontSize: 14,
		color: COLORS.text,
	},
	headerActions: {
		flexDirection: "row",
		alignItems: "center",
	},
	headerIconButton: {
		marginLeft: 20,
		padding: 10,
	},
	heatNavButton: {
		paddingHorizontal: 15,
	},
	selectedDqItem: {
		backgroundColor: COLORS.primary,
	},
	selectedDqText: {
		color: COLORS.white,
	},
	versionText: {
		position: "absolute",
		left: 10,
		top: 2,
		fontSize: 8,
		color: "#CCCCCC", // Lighter gray for visibility on blue
	},
	footer: {
		padding: 5,
		alignItems: "center",
		borderTopWidth: 1,
		borderTopColor: "#EEEEEE",
	},
	footerText: {
		fontSize: 10,
		color: COLORS.secondary,
	},
	offlineModal: {
		borderRadius: 15,
		maxHeight: "60%",
		width: "90%",
		alignSelf: "center",
	},
	pendingItem: {
		paddingVertical: 10,
		borderBottomWidth: 1,
		borderBottomColor: COLORS.lightGray,
	},
	pendingText: {
		fontSize: 14,
		fontWeight: "bold",
	},
	pendingCodes: {
		fontSize: 12,
		color: COLORS.accent,
		marginTop: 2,
		fontWeight: "bold",
	},
	pendingCard: {
		flexDirection: "row",
		alignItems: "center",
		backgroundColor: COLORS.lightGray,
		marginBottom: 10,
		borderRadius: 8,
		borderWidth: 1,
		borderColor: "#E0E0E0",
		overflow: "hidden",
	},
	pendingInfo: {
		flex: 1,
		padding: 15,
	},
	deletePendingButton: {
		padding: 15,
		backgroundColor: "#FFE5E5",
		borderRightWidth: 1,
		borderRightColor: "#E0E0E0",
		justifyContent: "center",
		alignItems: "center",
		height: "100%",
	},
	pendingNote: {
		fontSize: 12,
		color: COLORS.secondary,
		fontStyle: "italic",
		marginTop: 4,
	},
});
