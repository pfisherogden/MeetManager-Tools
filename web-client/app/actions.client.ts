// Client-side implementation of actions for static export mode (Tauri compilation)
import { callRestGateway, getRestPort } from "@/lib/tauri-bridge";

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
		pdfContentBase64: response.pdfContent || response.pdf_content || null,
		htmlContent: response.htmlContent || response.html_content || "",
		filename: response.filename,
	};
}

export async function getTeams() {
	try {
		const response = await callRestGateway("GetTeams", {});
		return {
			teams: (response.teams || []).map((t: any) => ({
				id: t.id !== undefined ? t.id : "",
				name: t.name || "",
				code: t.code || "",
				city: t.city || "",
				state: t.state || "",
				athleteCount:
					t.athlete_count !== undefined
						? t.athlete_count
						: t.athleteCount !== undefined
							? t.athleteCount
							: 0,
				color: t.color || "",
			})),
		};
	} catch (_err) {
		return { teams: [] };
	}
}

export async function getTeam(id: number) {
	try {
		const response = await callRestGateway("GetTeam", { id });
		if (!response?.team) return null;
		const t = response.team;
		return {
			team: {
				id: t.id !== undefined ? t.id : "",
				name: t.name || "",
				code: t.code || "",
				lsc: t.lsc || "",
				city: t.city || "",
				state: t.state || "",
				athleteCount:
					t.athlete_count !== undefined
						? t.athlete_count
						: t.athleteCount !== undefined
							? t.athleteCount
							: 0,
				color: t.color || "",
			},
		};
	} catch (_err) {
		return null;
	}
}

export async function getMeets() {
	try {
		const response = await callRestGateway("GetMeets", {});
		return {
			meets: (response.meets || []).map((m: any) => ({
				id: m.id !== undefined ? m.id : "",
				name: m.name || "",
				location: m.location || "",
				startDate:
					m.start_date !== undefined
						? m.start_date
						: m.startDate !== undefined
							? m.startDate
							: "",
				endDate:
					m.end_date !== undefined
						? m.end_date
						: m.endDate !== undefined
							? m.endDate
							: "",
				course: m.course || "",
				status: m.status || "",
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
				id: a.id !== undefined ? a.id : "",
				firstName:
					a.first_name !== undefined
						? a.first_name
						: a.firstName !== undefined
							? a.firstName
							: "",
				lastName:
					a.last_name !== undefined
						? a.last_name
						: a.lastName !== undefined
							? a.lastName
							: "",
				teamId:
					a.team_id !== undefined
						? a.team_id
						: a.teamId !== undefined
							? a.teamId
							: "",
				teamName:
					a.team_name !== undefined
						? a.team_name
						: a.teamName !== undefined
							? a.teamName
							: "",
				gender: a.gender || "",
				age: a.age !== undefined ? a.age : 0,
				dateOfBirth:
					a.date_of_birth !== undefined
						? a.date_of_birth
						: a.dateOfBirth !== undefined
							? a.dateOfBirth
							: "",
				regNo:
					a.reg_no !== undefined
						? a.reg_no
						: a.regNo !== undefined
							? a.regNo
							: "",
				schoolYear:
					a.school_year !== undefined
						? a.school_year
						: a.schoolYear !== undefined
							? a.schoolYear
							: "",
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
				id: e.id !== undefined ? e.id : "",
				eventNo:
					e.event_no !== undefined
						? e.event_no
						: e.eventNo !== undefined
							? e.eventNo
							: "",
				name: e.name || "",
				gender: e.gender || "",
				ageGroup:
					e.age_group !== undefined
						? e.age_group
						: e.ageGroup !== undefined
							? e.ageGroup
							: "",
				distance: e.distance !== undefined ? e.distance : 0,
				stroke: e.stroke || "",
				session: e.session || "",
				status: e.status || "",
				entryCount:
					e.entry_count !== undefined
						? e.entry_count
						: e.entryCount !== undefined
							? e.entryCount
							: 0,
				isRelay:
					e.is_relay !== undefined
						? e.is_relay
						: e.isRelay !== undefined
							? e.isRelay
							: false,
				lowAge:
					e.low_age !== undefined
						? e.low_age
						: e.lowAge !== undefined
							? e.lowAge
							: 0,
				highAge:
					e.high_age !== undefined
						? e.high_age
						: e.highAge !== undefined
							? e.highAge
							: 0,
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
				id: s.id !== undefined ? s.id : "",
				meetId:
					s.meet_id !== undefined
						? s.meet_id
						: s.meetId !== undefined
							? s.meetId
							: "",
				sessionNum:
					s.session_num !== undefined
						? s.session_num
						: s.sessionNum !== undefined
							? s.sessionNum
							: 0,
				name: s.name || "",
				date: s.date || "",
				startTime:
					s.start_time !== undefined
						? s.start_time
						: s.startTime !== undefined
							? s.startTime
							: "",
				warmUpTime:
					s.warm_up_time !== undefined
						? s.warm_up_time
						: s.warmUpTime !== undefined
							? s.warmUpTime
							: "",
				eventCount:
					s.event_count !== undefined
						? s.event_count
						: s.eventCount !== undefined
							? s.eventCount
							: 0,
				day: s.day || "",
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
				id: r.id !== undefined ? r.id : "",
				eventId:
					r.event_id !== undefined
						? r.event_id
						: r.eventId !== undefined
							? r.eventId
							: "",
				teamId:
					r.team_id !== undefined
						? r.team_id
						: r.teamId !== undefined
							? r.teamId
							: "",
				teamName:
					r.team_name !== undefined
						? r.team_name
						: r.teamName !== undefined
							? r.teamName
							: "",
				leg1Name:
					r.leg1_name !== undefined
						? r.leg1_name
						: r.leg1Name !== undefined
							? r.leg1Name
							: "",
				leg2Name:
					r.leg2_name !== undefined
						? r.leg2_name
						: r.leg2Name !== undefined
							? r.leg2Name
							: "",
				leg3Name:
					r.leg3_name !== undefined
						? r.leg3_name
						: r.leg3Name !== undefined
							? r.leg3Name
							: "",
				leg4Name:
					r.leg4_name !== undefined
						? r.leg4_name
						: r.leg4Name !== undefined
							? r.leg4Name
							: "",
				seedTime:
					r.seed_time !== undefined
						? r.seed_time
						: r.seedTime !== undefined
							? r.seedTime
							: "",
				finalTime:
					r.final_time !== undefined
						? r.final_time
						: r.finalTime !== undefined
							? r.finalTime
							: "",
				place: r.place !== undefined ? r.place : 0,
				eventName:
					r.event_name !== undefined
						? r.event_name
						: r.eventName !== undefined
							? r.eventName
							: "",
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
				teamId:
					s.team_id !== undefined
						? s.team_id
						: s.teamId !== undefined
							? s.teamId
							: "",
				teamName:
					s.team_name !== undefined
						? s.team_name
						: s.teamName !== undefined
							? s.teamName
							: "",
				individualPoints:
					s.individual_points !== undefined
						? s.individual_points
						: s.individualPoints !== undefined
							? s.individualPoints
							: 0,
				relayPoints:
					s.relay_points !== undefined
						? s.relay_points
						: s.relayPoints !== undefined
							? s.relayPoints
							: 0,
				totalPoints:
					s.total_points !== undefined
						? s.total_points
						: s.totalPoints !== undefined
							? s.totalPoints
							: 0,
				rank: s.rank !== undefined ? s.rank : 0,
				meetName:
					s.meet_name !== undefined
						? s.meet_name
						: s.meetName !== undefined
							? s.meetName
							: "",
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
			eventScores: (response.event_scores || response.eventScores || []).map(
				(es: any) => ({
					eventId:
						es.event_id !== undefined
							? es.event_id
							: es.eventId !== undefined
								? es.eventId
								: "",
					eventName:
						es.event_name !== undefined
							? es.event_name
							: es.eventName !== undefined
								? es.eventName
								: "",
					entries: (es.entries || []).map((e: any) => ({
						id: e.id !== undefined ? e.id : "",
						eventId:
							e.event_id !== undefined
								? e.event_id
								: e.eventId !== undefined
									? e.eventId
									: "",
						athleteId:
							e.athlete_id !== undefined
								? e.athlete_id
								: e.athleteId !== undefined
									? e.athleteId
									: "",
						athleteName:
							e.athlete_name !== undefined
								? e.athlete_name
								: e.athleteName !== undefined
									? e.athleteName
									: "",
						teamId:
							e.team_id !== undefined
								? e.team_id
								: e.teamId !== undefined
									? e.teamId
									: "",
						teamName:
							e.team_name !== undefined
								? e.team_name
								: e.teamName !== undefined
									? e.teamName
									: "",
						seedTime:
							e.seed_time !== undefined
								? e.seed_time
								: e.seedTime !== undefined
									? e.seedTime
									: "",
						finalTime:
							e.final_time !== undefined
								? e.final_time
								: e.finalTime !== undefined
									? e.finalTime
									: "",
						place: e.place !== undefined ? e.place : 0,
						points: e.points !== undefined ? e.points : 0,
						eventName:
							e.event_name !== undefined
								? e.event_name
								: e.eventName !== undefined
									? e.eventName
									: "",
						heat: e.heat !== undefined ? e.heat : 0,
						lane: e.lane !== undefined ? e.lane : 0,
						status: e.status || "",
					})),
				}),
			),
		};
	} catch (_err) {
		return { eventScores: [] };
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
				filename: d.filename || "",
				isActive:
					d.is_active !== undefined
						? d.is_active
						: d.isActive !== undefined
							? d.isActive
							: false,
				lastModified:
					d.last_modified !== undefined
						? d.last_modified
						: d.lastModified !== undefined
							? d.lastModified
							: 0,
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
		jobId: response.jobId || response.job_id,
		filename: response.filename,
	};
}

const jobStatusMap: Record<string | number, number> = {
	JOB_STATUS_UNSPECIFIED: 0,
	JOB_STATUS_PENDING: 1,
	JOB_STATUS_PROCESSING: 2,
	JOB_STATUS_COMPLETED: 3,
	JOB_STATUS_FAILED: 4,
	0: 0,
	1: 1,
	2: 2,
	3: 3,
	4: 4,
};

export async function getJobStatus(jobId: string) {
	const response = await callRestGateway("GetJobStatus", { jobId });
	const rawStatus = response.status;
	const numericStatus =
		jobStatusMap[rawStatus] !== undefined ? jobStatusMap[rawStatus] : 0;
	return {
		status: numericStatus,
		progress: response.progress,
		message: response.message,
		bundleUrl: response.bundleUrl || response.bundle_url,
		googleSheetUrls:
			response.googleSheetUrls || response.google_sheet_urls || [],
	};
}

export async function getDashboardStats() {
	try {
		const response = await callRestGateway("GetDashboardStats", {});
		return {
			meetCount:
				response.meet_count !== undefined
					? response.meet_count
					: response.meetCount !== undefined
						? response.meetCount
						: 0,
			teamCount:
				response.team_count !== undefined
					? response.team_count
					: response.teamCount !== undefined
						? response.teamCount
						: 0,
			athleteCount:
				response.athlete_count !== undefined
					? response.athlete_count
					: response.athleteCount !== undefined
						? response.athleteCount
						: 0,
			eventCount:
				response.event_count !== undefined
					? response.event_count
					: response.eventCount !== undefined
						? response.eventCount
						: 0,
			totalAthletes:
				response.total_athletes !== undefined
					? response.total_athletes
					: response.totalAthletes !== undefined
						? response.totalAthletes
						: 0,
			totalTeams:
				response.total_teams !== undefined
					? response.total_teams
					: response.totalTeams !== undefined
						? response.totalTeams
						: 0,
			totalEvents:
				response.total_events !== undefined
					? response.total_events
					: response.totalEvents !== undefined
						? response.totalEvents
						: 0,
			totalResults:
				response.total_results !== undefined
					? response.total_results
					: response.totalResults !== undefined
						? response.totalResults
						: 0,
		};
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

export async function publishMeetData(_filename: string, _baseUrl: string) {
	const restPort = await getRestPort();
	const localUrl = `http://localhost:${restPort}`;
	const response = await callRestGateway("PublishMeetData", {
		frontendUrl: localUrl,
	});
	return {
		success: response.success,
		message: response.message,
		judgeAppUrl: response.judge_app_url || response.judgeAppUrl,
	};
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
		const response = await callRestGateway("GetAthlete", { id });
		if (!response?.athlete) return null;
		const a = response.athlete;
		return {
			athlete: {
				id: a.id !== undefined ? a.id : "",
				firstName:
					a.first_name !== undefined
						? a.first_name
						: a.firstName !== undefined
							? a.firstName
							: "",
				lastName:
					a.last_name !== undefined
						? a.last_name
						: a.lastName !== undefined
							? a.lastName
							: "",
				teamId:
					a.team_id !== undefined
						? a.team_id
						: a.teamId !== undefined
							? a.teamId
							: "",
				teamName:
					a.team_name !== undefined
						? a.team_name
						: a.teamName !== undefined
							? a.teamName
							: "",
				gender: a.gender || "",
				age: a.age !== undefined ? a.age : 0,
				dateOfBirth:
					a.date_of_birth !== undefined
						? a.date_of_birth
						: a.dateOfBirth !== undefined
							? a.dateOfBirth
							: "",
				regNo:
					a.reg_no !== undefined
						? a.reg_no
						: a.regNo !== undefined
							? a.regNo
							: "",
				schoolYear:
					a.school_year !== undefined
						? a.school_year
						: a.schoolYear !== undefined
							? a.schoolYear
							: "",
			},
		};
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
			entries: (response.entries || []).map((e: any) => ({
				id: e.id !== undefined ? e.id : "",
				eventId:
					e.event_id !== undefined
						? e.event_id
						: e.eventId !== undefined
							? e.eventId
							: "",
				athleteId:
					e.athlete_id !== undefined
						? e.athlete_id
						: e.athleteId !== undefined
							? e.athleteId
							: "",
				athleteName:
					e.athlete_name !== undefined
						? e.athlete_name
						: e.athleteName !== undefined
							? e.athleteName
							: "",
				teamId:
					e.team_id !== undefined
						? e.team_id
						: e.teamId !== undefined
							? e.teamId
							: "",
				teamName:
					e.team_name !== undefined
						? e.team_name
						: e.teamName !== undefined
							? e.teamName
							: "",
				seedTime:
					e.seed_time !== undefined
						? e.seed_time
						: e.seedTime !== undefined
							? e.seedTime
							: "",
				finalTime:
					e.final_time !== undefined
						? e.final_time
						: e.finalTime !== undefined
							? e.finalTime
							: "",
				place: e.place !== undefined ? e.place : 0,
				points: e.points !== undefined ? e.points : 0,
				eventName:
					e.event_name !== undefined
						? e.event_name
						: e.eventName !== undefined
							? e.eventName
							: "",
				heat: e.heat !== undefined ? e.heat : 0,
				lane: e.lane !== undefined ? e.lane : 0,
				status: e.status || "",
			})),
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
		return { disqualifications: response.disqualifications || [] };
	} catch (_err) {
		return { disqualifications: [] };
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
		const response = await callRestGateway("ValidateMeet", {});
		return {
			success: response.success ?? true,
			message: response.message || "",
			findings: (response.findings || []).map((f: any) => {
				let severity = f.severity;
				if (typeof severity === "string") {
					const s = severity.toUpperCase().trim();
					if (s === "VALIDATION_SEVERITY_CRITICAL" || s === "CRITICAL") {
						severity = 3;
					} else if (s === "VALIDATION_SEVERITY_WARNING" || s === "WARNING") {
						severity = 2;
					} else if (s === "VALIDATION_SEVERITY_INFO" || s === "INFO") {
						severity = 1;
					} else {
						severity = 0;
					}
				}
				return {
					severity: typeof severity === "number" ? severity : 0,
					category: f.category,
					message: f.message,
					affectedId: f.affected_id ?? f.affectedId ?? "",
				};
			}),
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
	try {
		return await callRestGateway("GetGoogleConfig", {});
	} catch (_err) {
		return null;
	}
}

export async function resolveBundleUrl(bundleUrl: string): Promise<string> {
	if (!bundleUrl) return "";
	const restPort = await getRestPort();
	if (bundleUrl.startsWith("/")) {
		return `http://localhost:${restPort}${bundleUrl}`;
	}
	try {
		const url = new URL(bundleUrl);
		if (
			url.hostname === "localhost" ||
			url.hostname === "127.0.0.1" ||
			url.protocol === "tauri:"
		) {
			url.protocol = "http:";
			url.host = `localhost:${restPort}`;
			return url.toString();
		}
	} catch (_e) {}
	return bundleUrl;
}
