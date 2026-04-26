"use server";

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
import { Metadata } from "nice-grpc";
import client from "@/lib/mm-client";

async function getAuthMetadata() {
	const headerList = await headers();
	let userId = headerList.get("x-user-id");

	// Fallback for local development or E2E bypass
	if (process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true" && !userId) {
		userId = "e2e-bypass-user";
		console.log(`DEBUG: E2E Auth Bypass triggered for user: ${userId}`);
	}

	if (!userId) {
		throw new Error("User ID is required. Please sign in.");
	}

	const metadata = new Metadata();
	metadata.set("x-user-id", userId);
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
				gender: a.gender,
				age: a.age,
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
				eventNo: e.id,
				gender: e.gender,
				ageGroup: e.ageGroup,
				distance: e.distance,
				stroke: e.stroke,
				isRelay: false, // Placeholder, update if needed
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
				sessionNo: s.sessionNum,
				name: s.name,
				startTime: s.startTime,
			})),
		};
	} catch (_err) {
		return { sessions: [] };
	}
}

export async function getRelays() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getRelays({}, { metadata });
		return {
			relays: response.relays.map((r) => ({
				id: r.id,
				eventNo: r.eventId,
				teamId: r.teamId,
				relayLetter: r.relayLetter,
				swimmers: [r.leg1Name, r.leg2Name, r.leg3Name, r.leg4Name].filter(
					Boolean,
				),
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
			teamScores: response.scores.map((ts) => ({
				teamId: ts.teamId,
				teamName: ts.teamName,
				score: ts.totalPoints,
				rank: ts.rank,
			})),
		};
	} catch (_err) {
		return { teamScores: [] };
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
				entries: es.entries.map((entry) => ({
					athleteName: entry.athleteName,
					teamName: entry.teamName,
					finalTime: entry.finalTime,
					place: entry.place,
					points: entry.points,
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

	// Extra wait for backend stability in local docker environments
	if (process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true") {
		console.log("E2E DEBUG: Artificial startup delay (10s)...");
		await new Promise((r) => setTimeout(r, 10000));
	}

	try {
		const buffer = await file.arrayBuffer();
		const uint8Array = new Uint8Array(buffer);

		// Fix for client-streaming method: must pass an AsyncIterable
		async function* requestGenerator() {
			yield {
				filename: file.name,
				content: uint8Array,
			};
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
	} catch (_err) {
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
		const _response = await client.clearDataset({ filename }, { metadata });
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
) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.generateReportBundle(
			{
				reports: requests.map((r) => ({
					type: r.type,
					title: r.title,
					teamFilter: r.teamFilter || "",
					genderFilter: r.genderFilter,
					ageGroupFilter: r.ageGroupFilter,
					columnsOnPage: r.columnsOnPage,
					showRelaySwimmers: r.showRelaySwimmers,
					zebraStriping: r.zebraStriping,
					rendererType: r.rendererType || 0,
					htmlPreview: r.htmlPreview || false,
				})),
				bundleName,
				rendererType: 0,
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
		return await client.getDashboardStats({}, { metadata });
	} catch (_err) {
		return { totalAthletes: 0, totalTeams: 0, totalEvents: 0, totalResults: 0 };
	}
}

export async function publishMeetData(_filename: string) {
	try {
		const metadata = await getAuthMetadata();
		// The proto expects frontend_url to generate the full link
		const frontendUrl = process.env.FRONTEND_URL || "http://localhost:3000";
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

export async function getEntries() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getEntries({}, { metadata });
		return { entries: response.entries || [] };
	} catch (_err) {
		return { entries: [] };
	}
}

export async function updateAdminConfig(_config: any) {
	// Legacy placeholder to satisfy imports during build
	return { success: true };
}

export async function getDisqualifications() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getDisqualifications({}, { metadata });
		return { disqualifications: response.disqualifications || [] };
	} catch (_err) {
		return { disqualifications: [] };
	}
}
