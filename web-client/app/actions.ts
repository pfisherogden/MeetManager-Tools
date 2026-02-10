'use server'

import client from "@/lib/mm-client";
import { Empty, DatasetRequest } from "@/lib/proto/meet_manager";

import { revalidatePath } from 'next/cache';

export async function listDatasets() {
    try {
        const response = await client.listDatasets(Empty.fromPartial({}));
        console.log("SERVER ACTION SUCCESS (listDatasets):", response);
        return response;
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (listDatasets):", err);
        throw new Error(err.message);
    }
}

export async function setActiveDataset(filename: string) {
    try {
        await client.setActiveDataset({ filename });
        revalidatePath('/', 'layout');
        return true;
    } catch (err: any) {
        throw new Error(err.message);
    }
}

export async function uploadDataset(formData: FormData) {
    console.log("SERVER ACTION: uploadDataset called");
    const file = formData.get('file') as File;
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
        revalidatePath('/', 'layout');
        return response;
    } catch (err: any) {
        console.error("SERVER ACTION: Upload Error:", err);
        throw new Error(err.message);
    }
}

export async function getSessions() {
    try {
        return await client.getSessions(Empty.fromPartial({}));
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (getSessions):", err);
        throw new Error(err.message);
    }
}

export async function getAdminConfig() {
    try {
        return await client.getAdminConfig(Empty.fromPartial({}));
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (getAdminConfig):", err);
        // Return empty default if fails, to avoid breaking UI?
        return { meetName: "", meetDescription: "" };
    }
}

export async function updateAdminConfig(meetName: string, meetDescription: string) {
    try {
        const response = await client.updateAdminConfig({ meetName, meetDescription });
        revalidatePath('/', 'layout');
        return response;
    } catch (err: any) {
        throw new Error(err.message);
    }
}

export async function getEntries() {
    try {
        return await client.getEntries(Empty.fromPartial({}));
    } catch (err) {
        return { entries: [] };
    }
}

export async function getRelays() {
    try {
        return await client.getRelays(Empty.fromPartial({}));
    } catch (err) {
        return { relays: [] };
    }
}

export async function getScores() {
    try {
        return await client.getScores(Empty.fromPartial({}));
    } catch (err) {
        return { scores: [] };
    }
}

export async function getEventScores() {
    try {
        return await client.getEventScores(Empty.fromPartial({}));
    } catch (err) {
        return { eventScores: [] };
    }
}

export async function getTeams() {
    try {
        return await client.getTeams(Empty.fromPartial({}));
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (getTeams):", err);
        throw new Error(err.message);
    }
}

export async function getAthletes() {
    try {
        return await client.getAthletes(Empty.fromPartial({}));
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (getAthletes):", err);
        throw new Error(err.message);
    }
}

export async function getEvents() {
    try {
        return await client.getEvents(Empty.fromPartial({}));
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (getEvents):", err);
        throw new Error(err.message);
    }
}

export async function getMeets() {
    try {
        return await client.getMeets(Empty.fromPartial({}));
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (getMeets):", err);
        throw new Error(err.message);
    }
}

export async function getDashboardStats() {
    try {
        const response = await client.getDashboardStats(Empty.fromPartial({}));
        return response;
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (getDashboardStats):", err);
        // Return zeros if fails
        return {
            meetCount: 0,
            teamCount: 0,
            athleteCount: 0,
            eventCount: 0
        };
    }
}

export async function getTeam(id: number) {
    try {
        return await client.getTeam({ id });
    } catch (err: any) {
        console.error(`SERVER ACTION ERROR (getTeam ${id}):`, err);
        // Return null or throw? Throwing is fine for now, page can handle error.
        throw new Error(err.message);
    }
}

export async function getAthlete(id: number) {
    try {
        return await client.getAthlete({ id });
    } catch (err: any) {
        console.error(`SERVER ACTION ERROR (getAthlete ${id}):`, err);
        throw new Error(err.message);
    }
}

export async function generateReport(type: number, title: string, teamFilter: string = "") {
    try {
        console.log(`Generating report: type=${type}, title=${title}, teamFilter=${teamFilter}`);
        // Using as any because local proto definitions might be out of sync
        const response = await (client as any).generateReport({
            type,
            title,
            teamFilter
        });

        if (!response.success) {
            throw new Error(response.message);
        }

        return {
            success: true,
            pdfContent: Array.from(response.pdfContent as Uint8Array), // Convert to regular array for serialization
            filename: response.filename
        };
    } catch (err: any) {
        console.error("SERVER ACTION ERROR (generateReport):", err);
        throw new Error(err.message);
    }
}
