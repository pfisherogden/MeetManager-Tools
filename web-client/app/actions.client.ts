import { type GenerateReportConfig } from "./actions";

// Dynamic backend URL resolver
const getBackendUrl = () => {
	// Standardize on loopback REST gateway
	const port = process.env.NEXT_PUBLIC_BACKEND_PORT || "8081";
	return `http://localhost:${port}`;
};

// Generic REST fetch helper to call backend endpoints without gRPC dependency
async function callGrpcRest(methodName: string, requestData: any = {}) {
	const url = `${getBackendUrl()}/api/grpc/${methodName}`;
	
	let userId = "dev-user";
	if (typeof window !== "undefined") {
		const userIdMatch = document.cookie.match(/x-user-id=([^;]+)/);
		if (userIdMatch) userId = userIdMatch[1];
	}

	const response = await fetch(url, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			"x-user-id": userId,
		},
		body: JSON.stringify(requestData),
	});

	if (!response.ok) {
		const text = await response.text();
		throw new Error(text || `HTTP error ${response.status}`);
	}

	return await response.json();
}

export async function generateReport(config: GenerateReportConfig) {
	try {
		const response = await callGrpcRest("GenerateReport", {
			type: config.type,
			title: config.title,
			teamFilter: config.teamFilter || "",
			genderFilter: config.genderFilter || "",
			ageGroupFilter: config.ageGroupFilter || "",
			columnsOnPage: config.columnsOnPage || 2,
			showRelaySwimmers: config.showRelaySwimmers !== false,
			zebraStriping: config.zebraStriping || false,
			rendererType: config.rendererType || 0,
			htmlPreview: config.htmlPreview || false,
			includeBlankLanes: config.includeBlankLanes !== false,
			breakEverySixEvents: config.breakEverySixEvents !== false,
		});

		return {
			success: response.success,
			message: response.message,
			pdfContentBase64: response.pdfContent || null,
			htmlContent: response.htmlContent || "",
			filename: response.filename,
		};
	} catch (err: any) {
		console.error("Client Action Error (generateReport):", err);
		throw new Error(err.message || "Failed to generate report");
	}
}

export async function getTeams() {
	try {
		const response = await callGrpcRest("GetTeams", {});
		return {
			teams: (response.teams || []).map((t: any) => ({
				id: t.id,
				name: t.name,
				shortName: t.shortName,
				code: t.code,
				lsc: t.lsc,
				athleteCount: t.athleteCount,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getTeams):", err);
		return { teams: [] };
	}
}

export async function getTeam(id: number) {
	try {
		const response = await callGrpcRest("GetTeam", { id });
		if (!response.team) return null;
		return {
			team: {
				id: response.team.id,
				name: response.team.name,
				shortName: response.team.shortName,
				code: response.team.code,
				lsc: response.team.lsc,
				athleteCount: response.team.athleteCount,
			},
			athletes: (response.athletes || []).map((a: any) => ({
				id: a.id,
				firstName: a.firstName,
				lastName: a.lastName,
				gender: a.gender,
				age: a.age,
				teamId: a.teamId,
				entryCount: a.entryCount,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getTeam):", err);
		return null;
	}
}

export async function getMeets() {
	try {
		const response = await callGrpcRest("GetMeets", {});
		return {
			meets: (response.meets || []).map((m: any) => ({
				id: m.id,
				name: m.name,
				title: m.title,
				startDate: m.startDate,
				endDate: m.endDate,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getMeets):", err);
		return { meets: [] };
	}
}

export async function getAthletes() {
	try {
		const response = await callGrpcRest("GetAthletes", {});
		return {
			athletes: (response.athletes || []).map((a: any) => ({
				id: a.id,
				firstName: a.firstName,
				lastName: a.lastName,
				gender: a.gender,
				age: a.age,
				teamId: a.teamId,
				teamName: a.teamName,
				entryCount: a.entryCount,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getAthletes):", err);
		return { athletes: [] };
	}
}

export async function getEvents() {
	try {
		const response = await callGrpcRest("GetEvents", {});
		return {
			events: (response.events || []).map((e: any) => ({
				id: e.id,
				number: e.number,
				gender: e.gender,
				distance: e.distance,
				stroke: e.stroke,
				ageGroup: e.ageGroup,
				isRelay: e.isRelay,
				heatCount: e.heatCount,
				entryCount: e.entryCount,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getEvents):", err);
		return { events: [] };
	}
}

export async function getSessions() {
	try {
		const response = await callGrpcRest("GetSessions", {});
		return {
			sessions: (response.sessions || []).map((s: any) => ({
				id: s.id,
				number: s.number,
				name: s.name,
				startTime: s.startTime,
				day: s.day,
				eventCount: s.eventCount,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getSessions):", err);
		return { sessions: [] };
	}
}

export async function getRelays(eventId?: string) {
	try {
		const response = await callGrpcRest("GetRelays", { eventId: eventId || "0" });
		return {
			relays: (response.relays || []).map((r: any) => ({
				id: r.id,
				eventId: r.eventId,
				teamId: r.teamId,
				teamName: r.teamName,
				entryTime: r.entryTime,
				heat: r.heat,
				lane: r.lane,
				athletes: (r.athletes || []).map((a: any) => ({
					id: a.id,
					firstName: a.firstName,
					lastName: a.lastName,
					gender: a.gender,
					age: a.age,
				})),
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getRelays):", err);
		return { relays: [] };
	}
}

export async function getScores() {
	try {
		const response = await callGrpcRest("GetScores", {});
		return {
			scores: (response.scores || []).map((s: any) => ({
				teamId: s.teamId,
				teamName: s.teamName,
				gender: s.gender,
				individualPoints: s.individualPoints,
				relayPoints: s.relayPoints,
				totalPoints: s.totalPoints,
				rank: s.rank,
				meetName: s.meetName,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getScores):", err);
		return { scores: [] };
	}
}

export async function getEventScores() {
	try {
		const response = await callGrpcRest("GetEventScores", {});
		return {
			eventScores: (response.eventScores || []).map((es: any) => ({
				eventId: es.eventId,
				eventName: es.eventName,
				entries: (es.entries || []).map((e: any) => ({
					id: e.id,
					eventId: e.eventId,
					athleteId: e.athleteId,
					athleteName: e.athleteName,
					teamId: e.teamId,
					teamName: e.teamName,
					seedTime: e.seedTime,
					finalTime: e.finalTime,
					place: e.place,
					points: e.points,
					eventName: e.eventName,
					heat: e.heat,
					lane: e.lane,
					status: e.status,
				})),
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getEventScores):", err);
		return { eventScores: [] };
	}
}

// Convert File to Base64 in standard Web environments
function fileToBase64(file: File): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.readAsDataURL(file);
		reader.onload = () => {
			const result = reader.result as string;
			// Strip the data URL prefix (e.g. "data:application/octet-stream;base64,")
			const base64 = result.substring(result.indexOf(",") + 1);
			resolve(base64);
		};
		reader.onerror = (error) => reject(error);
	});
}

export async function uploadDataset(formData: FormData) {
	const file = formData.get("file") as File;
	if (!file) throw new Error("No file provided");

	try {
		const base64Content = await fileToBase64(file);
		const response = await callGrpcRest("UploadDataset", {
			filename: file.name,
			content: base64Content,
		});
		return {
			success: response.success,
			message: response.message,
		};
	} catch (err: any) {
		console.error("Client Action Error (uploadDataset):", err);
		throw err;
	}
}

export async function uploadDatasetFromDrive(fileId: string, filename: string) {
	try {
		const response = await callGrpcRest("UploadDatasetFromDrive", { fileId, filename });
		return {
			success: response.success,
			message: response.message,
		};
	} catch (err: any) {
		console.error("Client Action Error (uploadDatasetFromDrive):", err);
		throw err;
	}
}

export async function listDatasets() {
	try {
		const response = await callGrpcRest("ListDatasets", {});
		return {
			datasets: (response.datasets || []).map((d: any) => ({
				filename: d.filename,
				isActive: d.isActive,
				lastModified: d.lastModified,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (listDatasets):", err);
		return { datasets: [] };
	}
}

export async function setActiveDataset(filename: string) {
	try {
		await callGrpcRest("SetActiveDataset", { filename });
		return {
			success: true,
			message: "Dataset activated",
		};
	} catch (err: any) {
		console.error("Client Action Error (setActiveDataset):", err);
		throw err;
	}
}

export async function deleteDataset(filename: string) {
	try {
		await callGrpcRest("ClearDataset", { filename });
		return {
			success: true,
			message: "Dataset deleted",
		};
	} catch (err: any) {
		console.error("Client Action Error (deleteDataset):", err);
		throw err;
	}
}

export async function generateReportBundle(
	requests: GenerateReportConfig[],
	bundleName: string,
	frontendUrl?: string,
) {
	try {
		const response = await callGrpcRest("GenerateReportBundle", {
			reports: requests.map((r) => ({
				type: r.type,
				title: r.title,
				teamFilter: r.teamFilter,
				genderFilter: r.genderFilter,
				ageGroupFilter: r.ageGroupFilter,
				columnsOnPage: r.columnsOnPage,
				showRelaySwimmers: r.showRelaySwimmers,
				zebraStriping: r.zebraStriping,
				rendererType: r.rendererType,
				htmlPreview: r.htmlPreview,
				includeBlankLanes: r.includeBlankLanes,
				breakEverySixEvents: r.breakEverySixEvents,
			})),
			bundleName,
			rendererType: requests[0]?.rendererType || 0,
			frontendUrl: frontendUrl || "",
		});

		return {
			success: response.success,
			message: response.message,
			jobId: response.jobId,
			filename: response.filename,
		};
	} catch (err: any) {
		console.error("Client Action Error (generateReportBundle):", err);
		throw err;
	}
}

export async function getJobStatus(jobId: string) {
	try {
		const response = await callGrpcRest("GetJobStatus", { jobId });
		return {
			status: response.status,
			progress: response.progress,
			message: response.message,
			bundleUrl: response.bundleUrl,
		};
	} catch (err: any) {
		console.error("Client Action Error (getJobStatus):", err);
		throw err;
	}
}

export async function getDashboardStats() {
	try {
		const response = await callGrpcRest("GetDashboardStats", {});
		return {
			meetCount: response.meetCount,
			teamCount: response.teamCount,
			athleteCount: response.athleteCount,
			eventCount: response.eventCount,
			totalAthletes: response.athleteCount,
			totalTeams: response.teamCount,
			totalEvents: response.eventCount,
			totalResults: response.meetCount,
		};
	} catch (err) {
		console.error("Client Action Error (getDashboardStats):", err);
		return {
			meetCount: 0,
			teamCount: 0,
			athleteCount: 0,
			eventCount: 0,
			totalAthletes: 0,
			totalTeams: 0,
			totalEvents: 0,
			totalResults: 0,
		};
	}
}

export async function publishMeetData(filename: string, frontendUrlOverride?: string) {
	try {
		const frontendUrl = frontendUrlOverride || "http://localhost:3100";
		const response = await callGrpcRest("PublishMeetData", { frontendUrl });
		return {
			success: response.success,
			message: response.message,
			judgeAppUrl: response.judgeAppUrl,
		};
	} catch (err: any) {
		console.error("Client Action Error (publishMeetData):", err);
		throw err;
	}
}

export async function getAdminConfig() {
	return { meetName: "MMTools", logoUrl: "" };
}

export async function getAthlete(id: number) {
	try {
		return await callGrpcRest("GetAthlete", { id });
	} catch (err) {
		console.error("Client Action Error (getAthlete):", err);
		return null;
	}
}

export async function getEntries(eventId?: string, athleteId?: string) {
	try {
		const response = await callGrpcRest("GetEntries", {
			eventId: eventId || "0",
			athleteId: athleteId || "0",
		});
		return { entries: response.entries || [] };
	} catch (err) {
		console.error("Client Action Error (getEntries):", err);
		return { entries: [] };
	}
}

export async function updateAdminConfig(_name: string, _desc?: string) {
	return { success: true };
}

// Local storage mocks for DQs in standalone client mode
export async function getDisqualifications() {
	try {
		const localData = localStorage.getItem("disqualifications");
		return { disqualifications: localData ? JSON.parse(localData) : [] };
	} catch (err) {
		console.error("Client Action Error (getDisqualifications):", err);
		return { disqualifications: [] };
	}
}

export async function deleteDq(dqId: string) {
	try {
		const localData = localStorage.getItem("disqualifications");
		let dqs = localData ? JSON.parse(localData) : [];
		dqs = dqs.filter((dq: any) => dq.clientDqId !== dqId);
		localStorage.setItem("disqualifications", JSON.stringify(dqs));
		return { success: true };
	} catch (err: any) {
		console.error("Client Action Error (deleteDq):", err);
		return { success: false, message: err.message };
	}
}

export async function clearAllDqs() {
	try {
		localStorage.removeItem("disqualifications");
		return { success: true };
	} catch (err: any) {
		console.error("Client Action Error (clearAllDqs):", err);
		return { success: false, message: err.message };
	}
}

export async function validateActiveMeet() {
	try {
		const response = await callGrpcRest("ValidateMeet", {});
		return {
			success: response.success,
			message: response.message,
			findings: (response.findings || []).map((f: any) => ({
				severity: f.severity,
				category: f.category,
				message: f.message,
				affectedId: f.affectedId,
			})),
		};
	} catch (err: any) {
		return {
			success: false,
			message: err.message || "Failed to validate meet.",
			findings: [],
		};
	}
}

export async function getGoogleConfig() {
	return {
		apiKey: "",
		clientId: "",
		appId: "39869978853",
	};
}
