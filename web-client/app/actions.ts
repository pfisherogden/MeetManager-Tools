"use server";

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
import client from "@/lib/mm-client";

async function getAuthMetadata() {
	const headerList = await headers();
	let userId = headerList.get("x-user-id");

	if (!userId) {
		// Fallback to cookie for resilience in some environments
		const { cookies } = await import("next/headers");
		const cookieStore = await cookies();
		userId = cookieStore.get("x-user-id")?.value;
	}

	// E2E Bypass for automated testing
	if (
		!userId &&
		(process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true" ||
			process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "1")
	) {
		// Try to extract uid from referer URL to maintain shard isolation in CI
		const referer = headerList.get("referer");
		if (referer) {
			try {
				const refererUrl = new URL(referer);
				userId = refererUrl.searchParams.get("uid");
			} catch (_e) {
				// Invalid URL, ignore
			}
		}

		if (!userId) {
			userId = "e2e-bypass-user";
		}
		console.log(`DEBUG: E2E Auth Bypass triggered for user: ${userId}`);
	}

	if (!userId) {
		const allHeaders = Array.from(headerList.entries())
			.map(([k, v]) => `${k}: ${v}`)
			.join(", ");
		console.error(`DEBUG: Auth failed. Headers present: ${allHeaders}`);
		throw new Error("Authentication required. Please refresh or log in again.");
	}

	return { "x-user-id": userId };
}

export async function listDatasets() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.listDatasets({}, { metadata });
		console.log("SERVER ACTION SUCCESS (listDatasets):", response);
		return response;
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (listDatasets):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function setActiveDataset(filename: string) {
	try {
		const metadata = await getAuthMetadata();
		await client.setActiveDataset({ filename }, { metadata });
		revalidatePath("/", "layout");
		return true;
	} catch (err: unknown) {
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function clearDataset(filename: string) {
	try {
		const metadata = await getAuthMetadata();
		await client.clearDataset({ filename }, { metadata });
		revalidatePath("/", "layout");
		return true;
	} catch (err: unknown) {
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function clearAllDatasets() {
	try {
		const metadata = await getAuthMetadata();
		await client.clearAllDatasets({}, { metadata });
		revalidatePath("/", "layout");
		return true;
	} catch (err: unknown) {
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function uploadDatasetFromDrive(fileId: string, filename: string) {
	// Sanitize fileId to prevent SSRF: Google Drive IDs are alphanumeric, underscores, and hyphens.
	if (!/^[a-zA-Z0-9_-]+$/.test(fileId)) {
		throw new Error("Invalid Google Drive file ID format.");
	}

	console.log(`SERVER ACTION: uploadDatasetFromDrive called for ${filename}`);

	const { cookies: nextCookies } = await import("next/headers");
	const cookieStore = await nextCookies();
	const googleAccessToken = cookieStore.get("googleAccessToken")?.value;

	if (!googleAccessToken) {
		throw new Error("Google access token not found. Please log in again.");
	}

	async function* driveUploadGenerator() {
		yield { filename };

		const response = await fetch(
			`https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`,
			{
				headers: {
					Authorization: `Bearer ${googleAccessToken}`,
				},
			},
		);

		if (!response.ok) {
			const errorText = await response.text();
			throw new Error(`Failed to fetch from Google Drive: ${errorText}`);
		}

		if (!response.body) {
			throw new Error("Google Drive response body is empty");
		}

		const reader = response.body.getReader();
		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				yield { chunk: value };
			}
		} finally {
			reader.releaseLock();
		}
	}

	try {
		const metadata = await getAuthMetadata();
		const response = await client.uploadDataset(driveUploadGenerator(), {
			metadata,
		});
		revalidatePath("/", "layout");
		return response;
	} catch (err: unknown) {
		console.error("SERVER ACTION: Drive Upload Error:", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function uploadDataset(formData: FormData) {
	console.log("SERVER ACTION: uploadDataset called");
	const file = formData.get("file") as File;
	if (!file) {
		throw new Error("No file uploaded");
	}

	async function* uploadRequestGenerator() {
		yield { filename: file.name };

		const stream = file.stream();
		const reader = stream.getReader();

		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				yield { chunk: value };
			}
		} finally {
			reader.releaseLock();
		}
	}

	try {
		const metadata = await getAuthMetadata();
		const response = await client.uploadDataset(uploadRequestGenerator(), {
			metadata,
		});
		revalidatePath("/", "layout");
		return response;
	} catch (err: unknown) {
		console.error("SERVER ACTION: Upload Error:", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getSessions() {
	try {
		const metadata = await getAuthMetadata();
		return await client.getSessions({}, { metadata });
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getSessions):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getAdminConfig() {
	try {
		const metadata = await getAuthMetadata();
		return await client.getAdminConfig({}, { metadata });
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getAdminConfig):", err);
		return { meetName: "", meetDescription: "" };
	}
}

export async function updateAdminConfig(
	meetName: string,
	meetDescription: string,
) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.updateAdminConfig(
			{
				meetName,
				meetDescription,
			},
			{ metadata },
		);
		revalidatePath("/", "layout");
		return response;
	} catch (err: unknown) {
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getEntries(eventId?: string, athleteId?: string) {
	try {
		const metadata = await getAuthMetadata();
		return await client.getEntries({ eventId, athleteId }, { metadata });
	} catch (_err) {
		return { entries: [] };
	}
}

export async function getRelays(eventId?: string) {
	try {
		const metadata = await getAuthMetadata();
		return await client.getRelays({ eventId }, { metadata });
	} catch (_err) {
		return { relays: [] };
	}
}

export async function getScores() {
	try {
		const metadata = await getAuthMetadata();
		return await client.getScores({}, { metadata });
	} catch (_err) {
		return { scores: [] };
	}
}

export async function getEventScores() {
	try {
		const metadata = await getAuthMetadata();
		return await client.getEventScores({}, { metadata });
	} catch (_err) {
		return { eventScores: [] };
	}
}

export async function getTeams() {
	try {
		const metadata = await getAuthMetadata();
		return await client.getTeams({}, { metadata });
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getTeams):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getAthletes() {
	try {
		const metadata = await getAuthMetadata();
		return await client.getAthletes({}, { metadata });
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getAthletes):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getEvents() {
	try {
		const metadata = await getAuthMetadata();
		return await client.getEvents({}, { metadata });
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getEvents):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getMeets() {
	try {
		const metadata = await getAuthMetadata();
		return await client.getMeets({}, { metadata });
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getMeets):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getDashboardStats() {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.getDashboardStats({}, { metadata });
		return response;
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getDashboardStats):", err);
		return {
			meetCount: 0,
			teamCount: 0,
			athleteCount: 0,
			eventCount: 0,
		};
	}
}

export async function getTeam(id: number) {
	try {
		const metadata = await getAuthMetadata();
		return await client.getTeam({ id }, { metadata });
	} catch (err: unknown) {
		console.error(`SERVER ACTION ERROR (getTeam ${id}):`, err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getAthlete(id: number) {
	try {
		const metadata = await getAuthMetadata();
		return await client.getAthlete({ id }, { metadata });
	} catch (err: unknown) {
		const safeId = Number.parseInt(String(id), 10);
		console.error(`SERVER ACTION ERROR (getAthlete ${safeId}):`, err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function generateReport(
	type: number,
	title: string,
	teamFilter: string = "",
	genderFilter?: string,
	ageGroupFilter?: string,
	columnsOnPage: number = 2,
	showRelaySwimmers: boolean = true,
	zebraStriping: boolean = false,
	_rendererType: number = 0,
) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.generateReport(
			{
				type,
				title,
				teamFilter,
				genderFilter,
				ageGroupFilter,
				columnsOnPage,
				showRelaySwimmers,
				zebraStriping,
			},
			{ metadata },
		);

		if (!response.success) {
			throw new Error(response.message);
		}

		return {
			success: true,
			pdfContentBase64: Buffer.from(response.pdfContent as Uint8Array).toString(
				"base64",
			),
			filename: response.filename,
			htmlContent: response.htmlContent,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (generateReport):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function generateReportBundle(
	reports: any[],
	bundleName: string = "bundle.zip",
	rendererType: number = 0,
) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.generateReportBundle(
			{
				reports: reports.map((r) => ({
					type: r.type,
					title: r.title,
					teamFilter: r.teamFilter || "",
					genderFilter: r.genderFilter,
					ageGroupFilter: r.ageGroupFilter,
					columnsOnPage: r.columnsOnPage || 2,
					showRelaySwimmers:
						r.showRelaySwimmers !== undefined ? r.showRelaySwimmers : true,
					zebraStriping: !!r.zebraStriping,
				})),
				bundleName,
				rendererType,
			},
			{ metadata },
		);

		if (!response.success) {
			throw new Error(response.message);
		}

		return {
			success: true,
			message: response.message,
			filename: response.filename,
			bundleUrl: response.bundleUrl,
			jobId: response.jobId,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (generateReportBundle):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
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
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getDisqualifications() {
	try {
		const { getDqs } = await import("@/lib/dq-db");
		return await getDqs();
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getDisqualifications):", err);
		throw new Error("Failed to fetch disqualifications");
	}
}

export async function publishMeetData(frontendUrl?: string) {
	try {
		const metadata = await getAuthMetadata();
		const response = await client.publishMeetData(
			{ frontendUrl: frontendUrl || "" },
			{ metadata },
		);
		if (!response.success) {
			throw new Error(response.message);
		}
		return {
			success: true,
			judgeAppUrl: response.judgeAppUrl,
		};
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (publishMeetData):", err);
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}
