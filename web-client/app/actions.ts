"use server";

import { revalidatePath } from "next/cache";
import client from "@/lib/mm-client";

export async function listDatasets() {
	try {
		const response = await client.listDatasets({});
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
		await client.setActiveDataset({ filename });
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
		await client.clearDataset({ filename });
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
		await client.clearAllDatasets({});
		revalidatePath("/", "layout");
		return true;
	} catch (err: unknown) {
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

	console.log(`Starting upload for ${file.name} (${file.size} bytes)`);

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
		const response = await client.uploadDataset(uploadRequestGenerator());
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
		return await client.getSessions({});
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
		return await client.getAdminConfig({});
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getAdminConfig):", err);
		// Return empty default if fails, to avoid breaking UI?
		return { meetName: "", meetDescription: "" };
	}
}

export async function updateAdminConfig(
	meetName: string,
	meetDescription: string,
) {
	try {
		const response = await client.updateAdminConfig({
			meetName,
			meetDescription,
		});
		revalidatePath("/", "layout");
		return response;
	} catch (err: unknown) {
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getEntries() {
	try {
		return await client.getEntries({});
	} catch (_err) {
		return { entries: [] };
	}
}

export async function getRelays() {
	try {
		return await client.getRelays({});
	} catch (_err) {
		return { relays: [] };
	}
}

export async function getScores() {
	try {
		return await client.getScores({});
	} catch (_err) {
		return { scores: [] };
	}
}

export async function getEventScores() {
	try {
		return await client.getEventScores({});
	} catch (_err) {
		return { eventScores: [] };
	}
}

export async function getTeams() {
	try {
		return await client.getTeams({});
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
		return await client.getAthletes({});
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
		return await client.getEvents({});
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
		return await client.getMeets({});
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
		const response = await client.getDashboardStats({});
		return response;
	} catch (err: unknown) {
		console.error("SERVER ACTION ERROR (getDashboardStats):", err);
		// Return zeros if fails
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
		return await client.getTeam({ id });
	} catch (err: unknown) {
		console.error(`SERVER ACTION ERROR (getTeam ${id}):`, err);
		// Return null or throw? Throwing is fine for now, page can handle error.
		if (err instanceof Error) {
			throw new Error(err.message);
		}
		throw new Error("An unknown error occurred");
	}
}

export async function getAthlete(id: number) {
	try {
		return await client.getAthlete({ id });
	} catch (err: unknown) {
		console.error(`SERVER ACTION ERROR (getAthlete ${id}):`, err);
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
) {
	try {
		console.log(
			`Generating report: type=${type}, title=${title}, teamFilter=${teamFilter}`,
		);
		const response = await client.generateReport({
			type,
			title,
			teamFilter,
		});

		if (!response.success) {
			throw new Error(response.message);
		}

		return {
			success: true,
			pdfContent: Array.from(response.pdfContent as Uint8Array), // Convert to regular array for serialization
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
