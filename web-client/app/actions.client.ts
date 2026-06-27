import Cookies from "js-cookie";

const BACKEND_PORT = process.env.NEXT_PUBLIC_BACKEND_PORT || "8081";
const BASE_URL = `http://localhost:${BACKEND_PORT}/api/grpc`;

async function callRESTGateway(methodName: string, payload: any = {}) {
	const userId = Cookies.get("x-user-id") || "dev-user";
	const idToken = Cookies.get("idToken") || "dev-token";
	const response = await fetch(`${BASE_URL}/${methodName}`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			"x-user-id": userId,
			Authorization: `Bearer ${idToken}`,
		},
		body: JSON.stringify(payload),
	});
	if (!response.ok) {
		const text = await response.text();
		throw new Error(
			`REST Gateway error for ${methodName}: ${response.status} - ${text}`,
		);
	}
	return response.json();
}

export async function generateReport(config: any) {
	return callRESTGateway("GenerateReport", config);
}

export async function getTeams() {
	const res = await callRESTGateway("GetTeams", {});
	return { teams: res.teams || [] };
}

export async function getTeam(id: number) {
	return callRESTGateway("GetTeam", { id });
}

export async function getMeets() {
	const res = await callRESTGateway("GetMeets", {});
	return { meets: res.meets || [] };
}

export async function getAthletes() {
	const res = await callRESTGateway("GetAthletes", {});
	return { athletes: res.athletes || [] };
}

export async function getEvents() {
	const res = await callRESTGateway("GetEvents", {});
	return { events: res.events || [], sessions: res.sessions || [] };
}

export async function getSessions() {
	const res = await callRESTGateway("GetSessions", {});
	return { sessions: res.sessions || [] };
}

export async function getRelays(eventId?: string) {
	const res = await callRESTGateway("GetRelays", { eventId: eventId || "0" });
	return { relays: res.relays || [] };
}

export async function getScores() {
	const res = await callRESTGateway("GetScores", {});
	return { scores: res.scores || [] };
}

export async function getEventScores() {
	const res = await callRESTGateway("GetEventScores", {});
	return { scores: res.scores || [] };
}

export async function uploadDataset(formData: FormData) {
	const file = formData.get("file") as File;
	if (!file) throw new Error("No file found in FormData");
	const buffer = await file.arrayBuffer();
	// Convert array buffer to base64 string
	const base64 = btoa(
		new Uint8Array(buffer).reduce(
			(data, byte) => data + String.fromCharCode(byte),
			"",
		),
	);
	return callRESTGateway("UploadDataset", {
		filename: file.name,
		content: base64,
	});
}

export async function uploadDatasetFromDrive(fileId: string, filename: string) {
	return callRESTGateway("UploadDatasetFromDrive", { fileId, filename });
}

export async function listDatasets() {
	const res = await callRESTGateway("ListDatasets", {});
	return { datasets: res.datasets || [] };
}

export async function setActiveDataset(filename: string) {
	return callRESTGateway("SetActiveDataset", { filename });
}

export async function deleteDataset(filename: string) {
	return callRESTGateway("ClearDataset", { filename });
}

export async function generateReportBundle(config: any) {
	return callRESTGateway("GenerateReportBundle", config);
}

export async function getJobStatus(jobId: string) {
	return callRESTGateway("GetJobStatus", { jobId });
}

export async function getDashboardStats() {
	return callRESTGateway("GetDashboardStats", {});
}

export async function publishMeetData(filename: string, baseUrl: string) {
	return callRESTGateway("PublishMeetData", { filename, baseUrl });
}

export async function getAdminConfig() {
	return callRESTGateway("GetAdminConfig", {});
}

export async function getAthlete(id: number) {
	return callRESTGateway("GetAthlete", { id });
}

export async function getEntries(eventId?: string, athleteId?: string) {
	const res = await callRESTGateway("GetEntries", {
		eventId: eventId || "0",
		athleteId: athleteId || "0",
	});
	return { entries: res.entries || [] };
}

export async function updateAdminConfig(_name: string, _desc?: string) {
	return { success: true };
}

export async function getDisqualifications() {
	if (typeof window === "undefined") return { disqualifications: [] };
	const data = localStorage.getItem("disqualifications") || "[]";
	const dqs = JSON.parse(data);
	return { disqualifications: dqs };
}

export async function deleteDq(dqId: string) {
	if (typeof window === "undefined") return { success: false };
	const data = localStorage.getItem("disqualifications") || "[]";
	let dqs = JSON.parse(data);
	dqs = dqs.filter((dq: any) => dq.id !== dqId);
	localStorage.setItem("disqualifications", JSON.stringify(dqs));
	return { success: true };
}

export async function clearAllDqs() {
	if (typeof window === "undefined") return { success: false };
	localStorage.setItem("disqualifications", "[]");
	return { success: true };
}

export async function validateActiveMeet() {
	const res = await callRESTGateway("ValidateMeet", {});
	return {
		success: res.success,
		message: res.message,
		findings: res.findings || [],
	};
}
