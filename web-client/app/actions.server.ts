"use server";

import { revalidatePath } from "next/cache";
import { cookies, headers } from "next/headers";
import { Metadata } from "nice-grpc";
import client from "@/lib/mm-client";

async function getAuthMetadata() {
	const headerList = await headers();
	const cookieStore = await cookies();
	let userId =
		headerList.get("x-user-id") || cookieStore.get("x-user-id")?.value;

	// Fallback for local development, desktop mode, or E2E bypass
	const isAuthDisabled =
		process.env.NEXT_PUBLIC_AUTH_DISABLED === "true" ||
		process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true";

	if (isAuthDisabled && !userId) {
		userId = "dev-user";
		if (process.env.NODE_ENV !== "production") {
			console.log(`DEBUG: Auth Bypass triggered for user: ${userId}`);
		}
	}

	if (!userId) {
		throw new Error("User ID is required. Please sign in.");
	}

	const metadata = new Metadata();
	metadata.set("x-user-id", userId);

	if (isAuthDisabled) {
		metadata.set("authorization", "Bearer dev-token");
	}
	return metadata;
}

// Named configuration object for better parameter safety
export interface GenerateReportConfig {
	type: number;
	title: string;
	teamFilter?: string;
	genderFilter?: string;
	ageGroupFilter?: string;
	columnsOnPage?: number;
	showRelaySwimmers?: boolean;
	zebraStriping?: boolean;
	rendererType?: number;
	htmlPreview?: boolean;
	includeBlankLanes?: boolean;
	breakEverySixEvents?: boolean;
}

export async function generateReport(config: GenerateReportConfig) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.generateReport(
			{
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
			},
			{ metadata },
		);

		return {
			success: response.success,
			message: response.message,
			pdfContentBase64: response.pdfContent
				? Buffer.from(response.pdfContent).toString("base64")
				: null,
			htmlContent: response.htmlContent || "",
			filename: response.filename,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (generateReport):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getTeams() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getTeams({}, { metadata });
		return {
			teams: response.teams.map((t) => ({
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
		const metadata = await getAuthMetadata();
		return await client.getTeam({ id }, { metadata });
	} catch (_err) {
		return null;
	}
}

export async function getMeets() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getMeets({}, { metadata });
		return {
			meets: response.meets.map((m) => ({
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
		const metadata = await getAuthMetadata();
		const response = await client.getAthletes({}, { metadata });
		return {
			athletes: response.athletes.map((a) => ({
				id: a.id,
				firstName: a.firstName,
				lastName: a.lastName,
				teamId: a.teamId,
				teamName: a.teamName,
				gender: a.gender,
				age: a.age,
				dateOfBirth: a.dateOfBirth,
				regNo: a.regNo,
				schoolYear: a.schoolYear,
			})),
		};
	} catch (_err) {
		return { athletes: [] };
	}
}

export async function getEvents() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getEvents({}, { metadata });
		return {
			events: response.events.map((e) => ({
				id: e.id,
				eventNo: e.eventNo,
				name: e.name,
				gender: e.gender,
				ageGroup: e.ageGroup,
				distance: e.distance,
				stroke: e.stroke,
				session: e.session,
				status: e.status,
				entryCount: e.entryCount,
				isRelay: e.isRelay,
				lowAge: e.lowAge,
				highAge: e.highAge,
			})),
		};
	} catch (_err) {
		return { events: [] };
	}
}

export async function getSessions() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getSessions({}, { metadata });
		return {
			sessions: response.sessions.map((s) => ({
				id: s.id,
				meetId: s.meetId,
				sessionNum: s.sessionNum,
				name: s.name,
				date: s.date,
				startTime: s.startTime,
				warmUpTime: s.warmUpTime,
				eventCount: s.eventCount,
				day: s.day,
			})),
		};
	} catch (_err) {
		return { sessions: [] };
	}
}

export async function getRelays(eventId?: string) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getRelays(
			{ eventId: eventId || "0" },
			{ metadata },
		);
		return {
			relays: response.relays.map((r) => ({
				id: r.id,
				eventId: r.eventId,
				teamId: r.teamId,
				teamName: r.teamName,
				leg1Name: r.leg1Name,
				leg2Name: r.leg2Name,
				leg3Name: r.leg3Name,
				leg4Name: r.leg4Name,
				seedTime: r.seedTime,
				finalTime: r.finalTime,
				place: r.place,
				eventName: r.eventName,
			})),
		};
	} catch (_err) {
		return { relays: [] };
	}
}

export async function getScores() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getScores({}, { metadata });
		return {
			scores: response.scores.map((s) => ({
				teamId: s.teamId,
				teamName: s.teamName,
				individualPoints: s.individualPoints,
				relayPoints: s.relayPoints,
				totalPoints: s.totalPoints,
				rank: s.rank,
				meetName: s.meetName,
			})),
		};
	} catch (_err) {
		return { scores: [] };
	}
}

export async function getEventScores() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getEventScores({}, { metadata });
		return {
			eventScores: response.eventScores.map((es) => ({
				eventId: es.eventId,
				eventName: es.eventName,
				entries: es.entries.map((e) => ({
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
	} catch (_err) {
		return { eventScores: [] };
	}
}

export async function uploadDataset(formData: FormData) {
	const file = formData.get("file") as File;
	const metadata = await getAuthMetadata();

	if (!file) throw new Error("No file provided");

	console.log(
		`E2E DEBUG: Server Action: uploadDataset for file ${file.name}, size ${file.size}`,
	);

	try {
		const buffer = await file.arrayBuffer();
		const uint8Array = new Uint8Array(buffer);

		// Fix for client-streaming method: must pass an AsyncIterable
		// Must respect 'oneof data' in UploadDatasetRequest (filename OR chunk)
		async function* requestGenerator() {
			// First message: filename
			yield { filename: file.name };

			// Subsequent messages: chunks (1MB chunks to respect gRPC limits)
			const CHUNK_SIZE = 1024 * 1024; // 1MB
			for (let offset = 0; offset < uint8Array.length; offset += CHUNK_SIZE) {
				const chunk = uint8Array.slice(offset, offset + CHUNK_SIZE);
				yield { chunk: chunk };
			}
		}

		const response = await client.uploadDataset(requestGenerator(), {
			metadata,
		});

		console.log(
			`E2E DEBUG: Server Action: gRPC response: success=${response.success}`,
		);

		if (response.success) {
			// In E2E mode, we sometimes need an artificial delay for filesystem consistency
			if (process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true") {
				await new Promise((r) => setTimeout(r, 2000));
			}
			revalidatePath("/admin");
			revalidatePath("/meets");
			revalidatePath("/teams");
			revalidatePath("/reports");
		}

		return {
			success: response.success,
			message: response.message,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (uploadDataset):", err);
		throw err;
	}
}

export async function uploadDatasetFromDrive(fileId: string, filename: string) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.uploadDatasetFromDrive(
			{ fileId, filename },
			{ metadata },
		);

		if (response.success) {
			revalidatePath("/admin");
			revalidatePath("/meets");
			revalidatePath("/teams");
			revalidatePath("/reports");
		}

		return {
			success: response.success,
			message: response.message,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (uploadDatasetFromDrive):", err);
		throw err;
	}
}

export async function listDatasets() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.listDatasets({}, { metadata });
		return {
			datasets: response.datasets.map((d) => ({
				filename: d.filename,
				isActive: d.isActive,
				lastModified: d.lastModified,
			})),
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (listDatasets):", err);
		return { datasets: [] };
	}
}

export async function setActiveDataset(filename: string) {
	const metadata = await getAuthMetadata();
	try {
		await client.setActiveDataset({ filename }, { metadata });
		revalidatePath("/admin");
		revalidatePath("/meets");
		revalidatePath("/teams");
		revalidatePath("/reports");
		return {
			success: true,
			message: "Dataset activated",
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (setActiveDataset):", err);
		throw err;
	}
}

export async function deleteDataset(filename: string) {
	const metadata = await getAuthMetadata();
	try {
		await client.clearDataset({ filename }, { metadata });
		revalidatePath("/admin");
		return {
			success: true,
			message: "Dataset deleted",
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (deleteDataset):", err);
		throw err;
	}
}

export async function generateReportBundle(
	requests: GenerateReportConfig[],
	bundleName: string,
	frontendUrl?: string,
) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.generateReportBundle(
			{
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
			},
			{ metadata },
		);

		return {
			success: response.success,
			message: response.message,
			jobId: response.jobId,
			filename: response.filename,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (generateReportBundle):", err);
		throw err;
	}
}

export async function getJobStatus(jobId: string) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getJobStatus({ jobId }, { metadata });
		return {
			status: response.status,
			progress: response.progress,
			message: response.message,
			bundleUrl: response.bundleUrl,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getJobStatus):", err);
		throw err;
	}
}

export async function getDashboardStats() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getDashboardStats({}, { metadata });
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

export async function publishMeetData(
	_filename: string,
	frontendUrlOverride?: string,
) {
	try {
		const metadata = await getAuthMetadata();
		const frontendUrl =
			frontendUrlOverride ||
			process.env.FRONTEND_URL ||
			"http://localhost:3100";
		const response = await client.publishMeetData(
			{ frontendUrl },
			{ metadata },
		);
		return {
			success: response.success,
			message: response.message,
			judgeAppUrl: response.judgeAppUrl,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (publishMeetData):", err);
		throw err;
	}
}

export async function getAdminConfig() {
	return { meetName: "MMTools", logoUrl: "" };
}

export async function getAthlete(id: number) {
	const metadata = await getAuthMetadata();
	return await client.getAthlete({ id }, { metadata });
}

export async function getEntries(eventId?: string, athleteId?: string) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getEntries(
			{ eventId: eventId || "0", athleteId: athleteId || "0" },
			{ metadata },
		);
		return { entries: response.entries || [] };
	} catch (_err) {
		return { entries: [] };
	}
}

export async function updateAdminConfig(_name: string, _desc?: string) {
	return { success: true };
}

export async function getDisqualifications() {
	try {
		const headerList = await headers();
		const cookieStore = await cookies();
		const userId =
			headerList.get("x-user-id") || cookieStore.get("x-user-id")?.value;

		if (!userId) {
			console.warn("getDisqualifications: No userId found");
			return { disqualifications: [] };
		}

		const { getDqs } = await import("@/lib/dq-db");
		const dqs = await getDqs(userId);
		return { disqualifications: dqs };
	} catch (error) {
		console.error("Failed to get disqualifications:", error);
		return { disqualifications: [] };
	}
}

export async function deleteDq(dqId: string) {
	try {
		const headerList = await headers();
		const cookieStore = await cookies();
		const userId =
			headerList.get("x-user-id") || cookieStore.get("x-user-id")?.value;

		if (!userId) throw new Error("Unauthorized");

		const { deleteDq: deleteFromDb } = await import("@/lib/dq-db");
		await deleteFromDb(dqId, userId);
		revalidatePath("/dqs");
		return { success: true };
	} catch (error: any) {
		console.error("Failed to delete DQ:", error);
		return { success: false, message: error.message };
	}
}

export async function clearAllDqs() {
	try {
		const headerList = await headers();
		const cookieStore = await cookies();
		const userId =
			headerList.get("x-user-id") || cookieStore.get("x-user-id")?.value;

		if (!userId) throw new Error("Unauthorized");

		const { clearAllDqs: clearFromDb } = await import("@/lib/dq-db");
		await clearFromDb(userId);
		revalidatePath("/dqs");
		return { success: true };
	} catch (error: any) {
		console.error("Failed to clear all DQs:", error);
		return { success: false, message: error.message };
	}
}

export async function validateActiveMeet() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.validateMeet({}, { metadata });
		return {
			success: response.success,
			message: response.message,
			findings: response.findings.map((f) => ({
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
	const env = process.env;
	return {
		apiKey: env.GOOGLE_API_KEY || env.NEXT_PUBLIC_GOOGLE_API_KEY || "",
		clientId: env.GOOGLE_CLIENT_ID || env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "",
		appId:
			env.GOOGLE_APP_ID ||
			env.NEXT_PUBLIC_GOOGLE_APP_ID ||
			env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID ||
			"39869978853",
	};
}
