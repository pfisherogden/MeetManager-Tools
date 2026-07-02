import type { GenerateReportConfig } from "./actions";

let cachedPort: string | null = null;

if (typeof window !== "undefined") {
	const w = window as any;
	if (w.__TAURI_INTERNALS__ || w.__TAURI__) {
		import("@tauri-apps/api/core").then(({ invoke }) => {
			invoke<string>("get_backend_port")
				.then((p) => {
					cachedPort = p;
					console.log("Tauri dynamic port resolved:", p);
				})
				.catch((err) => {
					console.error("Failed to resolve Tauri dynamic port:", err);
				});
		});
	}
}

// Dynamic backend URL resolver
const getBackendUrl = () => {
	// Standardize on loopback REST gateway
	const port = cachedPort || process.env.NEXT_PUBLIC_BACKEND_PORT || "8081";
	return `http://127.0.0.1:${port}`;
};

// Helper function to recursively normalize snake_case keys to camelCase in responses
function normalizeKeys(obj: any): any {
	if (obj === null || typeof obj !== "object") {
		return obj;
	}
	if (Array.isArray(obj)) {
		return obj.map(normalizeKeys);
	}
	const normalized: any = {};
	for (const key of Object.keys(obj)) {
		const val = normalizeKeys(obj[key]);
		normalized[key] = val;
		if (key.includes("_")) {
			const camelKey = key.replace(/_([a-z0-9])/g, (g) => g[1].toUpperCase());
			if (!(camelKey in normalized)) {
				normalized[camelKey] = val;
			}
		}
	}
	return normalized;
}

// Generic REST fetch helper to call backend endpoints without gRPC dependency
async function callGrpcRest(methodName: string, requestData: any = {}) {
	const url = `${getBackendUrl()}/api/grpc/${methodName}`;

	let userId = "dev-user";
	if (typeof window !== "undefined") {
		// Fallback sequence: localStorage (for Tauri custom protocol) -> cookies -> dev-user
		userId = localStorage.getItem("x-user-id") || "";
		if (!userId) {
			const userIdMatch = document.cookie.match(/x-user-id=([^;]+)/);
			if (userIdMatch) userId = userIdMatch[1];
		}
		if (!userId) {
			userId = "dev-user";
		}
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

	const json = await response.json();
	return normalizeKeys(json);
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
			pdfContentBase64: response.pdf_content || null,
			htmlContent: response.html_content || "",
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
				code: t.code,
				athleteCount: t.athlete_count || 0,
				color: t.color || "",
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
				code: response.team.code,
				athleteCount: response.team.athlete_count || 0,
				color: response.team.color || "",
			},
			athletes: (response.athletes || []).map((a: any) => ({
				id: a.id,
				firstName: a.first_name,
				lastName: a.last_name,
				teamId: a.team_id,
				teamName: a.team_name,
				gender: a.gender,
				age: a.age,
				dateOfBirth: a.date_of_birth,
				regNo: a.reg_no,
				schoolYear: a.school_year,
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
				location: m.location,
				startDate: m.start_date,
				endDate: m.end_date,
				course: m.course,
				status: m.status,
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
				firstName: a.first_name,
				lastName: a.last_name,
				teamId: a.team_id,
				teamName: a.team_name,
				gender: a.gender,
				age: a.age,
				dateOfBirth: a.date_of_birth,
				regNo: a.reg_no,
				schoolYear: a.school_year,
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
				eventNo: e.event_no,
				name: e.name,
				gender: e.gender,
				ageGroup: e.age_group,
				distance: e.distance,
				stroke: e.stroke,
				session: e.session,
				status: e.status,
				entryCount: e.entry_count || 0,
				isRelay: e.is_relay,
				lowAge: e.low_age,
				highAge: e.high_age,
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
				meetId: s.meet_id,
				sessionNum: s.session_num,
				name: s.name,
				date: s.date,
				startTime: s.start_time,
				warmUpTime: s.warm_up_time,
				eventCount: s.event_count || 0,
				day: s.day,
			})),
		};
	} catch (err) {
		console.error("Client Action Error (getSessions):", err);
		return { sessions: [] };
	}
}

export async function getRelays(eventId?: string) {
	try {
		const response = await callGrpcRest("GetRelays", {
			eventId: eventId || "0",
		});
		return {
			relays: (response.relays || []).map((r: any) => ({
				id: r.id,
				eventId: r.event_id,
				teamId: r.team_id,
				teamName: r.team_name,
				leg1Name: r.leg1_name,
				leg2Name: r.leg2_name,
				leg3Name: r.leg3_name,
				leg4Name: r.leg4_name,
				seedTime: r.seed_time,
				finalTime: r.final_time,
				place: r.place,
				eventName: r.event_name,
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
				teamId: s.team_id,
				teamName: s.team_name,
				individualPoints: s.individual_points,
				relayPoints: s.relay_points,
				totalPoints: s.total_points,
				rank: s.rank,
				meetName: s.meet_name,
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
			eventScores: (response.event_scores || []).map((es: any) => ({
				eventId: es.event_id,
				eventName: es.event_name,
				entries: (es.entries || []).map((e: any) => ({
					id: e.id,
					eventId: e.event_id,
					athleteId: e.athlete_id,
					athleteName: e.athlete_name,
					teamId: e.team_id,
					teamName: e.team_name,
					seedTime: e.seed_time,
					finalTime: e.final_time,
					place: e.place,
					points: e.points,
					eventName: e.event_name,
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
		const response = await callGrpcRest("UploadDatasetFromDrive", {
			file_id: fileId,
			filename: filename,
		});
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
				isActive: d.is_active,
				lastModified: d.last_modified,
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
			jobId: response.job_id,
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
			bundleUrl: response.bundle_url,
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
			meetCount: response.meet_count || 0,
			teamCount: response.team_count || 0,
			athleteCount: response.athlete_count || 0,
			eventCount: response.event_count || 0,
			totalAthletes: response.athlete_count || 0,
			totalTeams: response.team_count || 0,
			totalEvents: response.event_count || 0,
			totalResults: response.meet_count || 0,
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

export async function publishMeetData(
	_filename: string,
	frontendUrlOverride?: string,
) {
	try {
		const frontendUrl = frontendUrlOverride || "http://localhost:3100";
		const response = await callGrpcRest("PublishMeetData", { frontendUrl });
		return {
			success: response.success,
			message: response.message,
			judgeAppUrl: response.judge_app_url,
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
		const response = await callGrpcRest("GetAthlete", { id });
		if (!response.athlete) return null;
		return {
			athlete: {
				id: response.athlete.id,
				firstName: response.athlete.first_name,
				lastName: response.athlete.last_name,
				teamId: response.athlete.team_id,
				teamName: response.athlete.team_name,
				gender: response.athlete.gender,
				age: response.athlete.age,
				dateOfBirth: response.athlete.date_of_birth,
				regNo: response.athlete.reg_no,
				schoolYear: response.athlete.school_year,
			},
		};
	} catch (err) {
		console.error("Client Action Error (getAthlete):", err);
		return null;
	}
}

export async function getEntries(eventId?: string, athleteId?: string) {
	try {
		const response = await callGrpcRest("GetEntries", {
			event_id: eventId || "0",
			athlete_id: athleteId || "0",
		});
		return {
			entries: (response.entries || []).map((e: any) => ({
				id: e.id,
				eventId: e.event_id,
				athleteId: e.athlete_id,
				athleteName: e.athlete_name,
				teamId: e.team_id,
				teamName: e.team_name,
				seedTime: e.seed_time,
				finalTime: e.final_time,
				place: e.place,
				points: e.points,
				eventName: e.event_name,
				heat: e.heat,
				lane: e.lane,
				status: e.status,
			})),
		};
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
				affectedId: f.affected_id,
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
