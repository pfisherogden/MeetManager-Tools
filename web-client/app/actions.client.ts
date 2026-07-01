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
	const res = await callRESTGateway("GenerateReport", config);
	return {
		success: res.success,
		message: res.message,
		pdfContentBase64: res.pdf_content || null,
		htmlContent: res.html_content || "",
		filename: res.filename,
		googleSheetUrl: res.google_sheet_url || null,
	};
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
	const base64 = await new Promise<string>((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => {
			const dataUrl = reader.result as string;
			const base64Data = dataUrl.split(",")[1];
			resolve(base64Data);
		};
		reader.onerror = (error) => reject(error);
		reader.readAsDataURL(file);
	});
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
	await callRESTGateway("SetActiveDataset", { filename });
	return { success: true };
}

export async function deleteDataset(filename: string) {
	await callRESTGateway("ClearDataset", { filename });
	return { success: true };
}

export async function generateReportBundle(
	requests: any[],
	bundleName: string,
	frontendUrl?: string,
) {
	const res = await callRESTGateway("GenerateReportBundle", {
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
		success: res.success,
		message: res.message,
		jobId: res.job_id || res.jobId,
	};
}

export async function getJobStatus(jobId: string) {
	const res = await callRESTGateway("GetJobStatus", { jobId });
	return {
		status: res.status,
		progress: res.progress,
		message: res.message,
		bundleUrl: res.bundle_url || res.bundleUrl,
		googleSheetUrls: res.google_sheet_urls || res.googleSheetUrls,
	};
}

export async function getDashboardStats() {
	return callRESTGateway("GetDashboardStats", {});
}

export async function publishMeetData(
	_filename: string,
	frontendUrlOverride?: string,
) {
	const res = await callRESTGateway("PublishMeetData", {
		frontendUrl: frontendUrlOverride || "",
	});
	return {
		success: res.success,
		message: res.message,
		judgeAppUrl: res.judge_app_url || res.judgeAppUrl,
	};
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
