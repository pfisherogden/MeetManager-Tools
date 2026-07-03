// Client-side implementation of actions for static export mode (Tauri compilation)
import { callRestGateway } from "@/lib/tauri-bridge";

export async function generateReport(config: any) {
	const payload = {
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
	};
	const response = await callRestGateway("GenerateReport", payload);
	return {
		success: response.success,
		message: response.message,
		pdfContentBase64: response.pdfContent || null,
		htmlContent: response.htmlContent || "",
		filename: response.filename,
	};
}

export async function getTeams() {
	try {
		const response = await callRestGateway("GetTeams", {});
		return {
			teams: (response.teams || []).map((t: any) => ({
				id: t.id,
				name: t.name,
				code: t.code,
				athleteCount: t.athleteCount,
				color: t.color,
			})),
		};
	} catch (_err) {
		return { teams: [] };
	}
}

export async function getTeam(id: number) {
	try {
		return await callRestGateway("GetTeam", { id });
	} catch (_err) {
		return null;
	}
}

export async function getMeets() {
	try {
		const response = await callRestGateway("GetMeets", {});
		return {
			meets: (response.meets || []).map((m: any) => ({
				id: m.id,
				name: m.name,
				location: m.location,
				startDate: m.startDate,
				endDate: m.endDate,
				course: m.course,
				status: m.status,
			})),
		};
	} catch (_err) {
		return { meets: [] };
	}
}

export async function getAthletes() {
	try {
		const response = await callRestGateway("GetAthletes", {});
		return {
			athletes: (response.athletes || []).map((a: any) => ({
				id: a.id,
				firstName: a.firstName,
				lastName: a.lastName,
				teamId: a.teamId,
			})),
		};
	} catch (_err) {
		return { athletes: [] };
	}
}

export async function getEvents() {
	try {
		const response = await callRestGateway("GetEvents", {});
		return {
			events: (response.events || []).map((e: any) => ({
				id: e.id,
				number: e.number,
				gender: e.gender,
				ageGroup: e.ageGroup,
				stroke: e.stroke,
				distance: e.distance,
				isRelay: e.isRelay,
				description: e.description,
			})),
		};
	} catch (_err) {
		return { events: [] };
	}
}

export async function getSessions() {
	try {
		const response = await callRestGateway("GetSessions", {});
		return {
			sessions: (response.sessions || []).map((s: any) => ({
				id: s.id,
				number: s.number,
				name: s.name,
				startTime: s.startTime,
				day: s.day,
			})),
		};
	} catch (_err) {
		return { sessions: [] };
	}
}

export async function getRelays(eventId?: string) {
	try {
		const response = await callRestGateway("GetRelays", {
			eventId: eventId || "",
		});
		return {
			relays: (response.relays || []).map((r: any) => ({
				id: r.id,
				eventId: r.eventId,
				teamId: r.teamId,
				number: r.number,
				swimmers: r.swimmers || [],
			})),
		};
	} catch (_err) {
		return { relays: [] };
	}
}

export async function getScores() {
	try {
		const response = await callRestGateway("GetScores", {});
		return {
			scores: (response.scores || []).map((s: any) => ({
				teamId: s.teamId,
				teamName: s.teamName,
				teamCode: s.teamCode,
				femaleScore: s.femaleScore,
				maleScore: s.maleScore,
				totalScore: s.totalScore,
			})),
		};
	} catch (_err) {
		return { scores: [] };
	}
}

export async function getEventScores() {
	try {
		const response = await callRestGateway("GetEventScores", {});
		return {
			scores: (response.scores || []).map((s: any) => ({
				eventId: s.eventId,
				teamId: s.teamId,
				teamName: s.teamName,
				teamCode: s.teamCode,
				points: s.points,
			})),
		};
	} catch (_err) {
		return { scores: [] };
	}
}

export async function uploadDataset(formData: FormData) {
	const file = formData.get("file") as File;
	if (!file) throw new Error("No file provided");

	const base64Content = await new Promise<string>((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => {
			const result = reader.result as string;
			const base64 = result.split(",")[1];
			resolve(base64);
		};
		reader.onerror = (err) => reject(reader.error || err);
		reader.readAsDataURL(file);
	});

	const response = await callRestGateway("UploadDataset", {
		filename: file.name,
		content: base64Content,
	});

	return {
		success: response.success,
		message: response.message,
	};
}

export async function uploadDatasetFromDrive(fileId: string, filename: string) {
	const response = await callRestGateway("UploadDatasetFromDrive", {
		fileId,
		filename,
	});
	return {
		success: response.success,
		message: response.message,
	};
}

export async function listDatasets() {
	try {
		const response = await callRestGateway("ListDatasets", {});
		return {
			datasets: (response.datasets || []).map((d: any) => ({
				filename: d.filename,
				isActive: d.isActive,
				lastModified: d.lastModified,
			})),
		};
	} catch (err) {
		console.error("Error listing datasets in client actions:", err);
		return { datasets: [] };
	}
}

export async function setActiveDataset(filename: string) {
	const response = await callRestGateway("SetActiveDataset", { filename });
	return {
		success: true,
		message: response.message || "Dataset activated",
	};
}

export async function deleteDataset(filename: string) {
	const response = await callRestGateway("ClearDataset", { filename });
	return {
		success: true,
		message: response.message || "Dataset deleted",
	};
}

export async function generateReportBundle(
	requests: any[],
	bundleName: string,
	frontendUrl?: string,
) {
	const payload = {
		reports: requests.map((r) => ({
			type: r.type,
			title: r.title,
			teamFilter: r.teamFilter || "",
			genderFilter: r.genderFilter || "",
			ageGroupFilter: r.ageGroupFilter || "",
			columnsOnPage: r.columnsOnPage || 2,
			showRelaySwimmers: r.showRelaySwimmers !== false,
			zebraStriping: r.zebraStriping || false,
			rendererType: r.rendererType || 0,
			htmlPreview: r.htmlPreview || false,
			includeBlankLanes: r.includeBlankLanes !== false,
			breakEverySixEvents: r.breakEverySixEvents !== false,
		})),
		bundleName,
		rendererType: requests[0]?.rendererType || 0,
		frontendUrl: frontendUrl || "",
	};
	const response = await callRestGateway("GenerateReportBundle", payload);
	return {
		success: response.success,
		message: response.message,
		jobId: response.jobId,
		filename: response.filename,
	};
}

export async function getJobStatus(jobId: string) {
	const response = await callRestGateway("GetJobStatus", { jobId });
	return {
		status: response.status,
		progress: response.progress,
		message: response.message,
		bundleUrl: response.bundleUrl,
	};
}

export async function getDashboardStats() {
	try {
		return await callRestGateway("GetDashboardStats", {});
	} catch (_err) {
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

export async function publishMeetData(filename: string, baseUrl: string) {
	return await callRestGateway("PublishMeetData", { filename, baseUrl });
}

export async function getAdminConfig() {
	try {
		return await callRestGateway("GetAdminConfig", {});
	} catch (_err) {
		return null;
	}
}

export async function getAthlete(id: number) {
	try {
		return await callRestGateway("GetAthlete", { id });
	} catch (_err) {
		return null;
	}
}

export async function getEntries(eventId?: string, athleteId?: string) {
	try {
		const response = await callRestGateway("GetEntries", {
			eventId: eventId || "",
			athleteId: athleteId || "",
		});
		return {
			entries: response.entries || [],
		};
	} catch (_err) {
		return { entries: [] };
	}
}

export async function updateAdminConfig(name: string, desc?: string) {
	return await callRestGateway("UpdateAdminConfig", { name, desc: desc || "" });
}

export async function getDisqualifications() {
	try {
		const response = await callRestGateway("GetDisqualifications", {});
		return response.disqualifications || [];
	} catch (_err) {
		return [];
	}
}

export async function deleteDq(dqId: string) {
	return await callRestGateway("DeleteDq", { dqId });
}

export async function clearAllDqs() {
	return await callRestGateway("ClearAllDqs", {});
}

export async function validateActiveMeet() {
	try {
		const response = await callRestGateway("ValidateActiveMeet", {});
		return {
			errors: response.errors || [],
		};
	} catch (_err) {
		return { errors: [] };
	}
}

export async function getGoogleConfig() {
	try {
		return await callRestGateway("GetGoogleConfig", {});
	} catch (_err) {
		return null;
	}
}
