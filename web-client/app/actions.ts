"use server";

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
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

	return { "x-user-id": userId };
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

export async function uploadDataset(formData: FormData) {
	const file = formData.get("file") as File;
	const metadata = await getAuthMetadata();

	if (!file) throw new Error("No file provided");

	try {
		const buffer = await file.arrayBuffer();
		const uint8Array = new Uint8Array(buffer);

		const response = await client.uploadDataset(
			{
				filename: file.name,
				content: uint8Array,
			},
			{ metadata },
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
		const response = await client.setActiveDataset({ filename }, { metadata });
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
		console.error("SERVER ACTION ERROR (setActiveDataset):", err);
		throw err;
	}
}

export async function deleteDataset(filename: string) {
	const metadata = await getAuthMetadata();
	try {
		const response = await client.deleteDataset({ filename }, { metadata });
		if (response.success) {
			revalidatePath("/admin");
		}
		return {
			success: response.success,
			message: response.message,
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
				requests: requests.map((r) => ({
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
				})),
				bundleName,
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

export async function publishMeetData(filename: string) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.publishMeetData({ filename }, { metadata });
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
