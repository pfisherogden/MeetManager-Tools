'use server'

import client from "@/lib/mm-client";
import { Empty, DatasetRequest } from "@/lib/proto/meet_manager";

import { revalidatePath } from 'next/cache';

export async function listDatasets() {
    return new Promise((resolve, reject) => {
        // @ts-ignore
        client.listDatasets(Empty.fromPartial({}), (err: any, response: any) => {
            if (err) {
                console.error("SERVER ACTION ERROR (listDatasets):", err);
                reject(err.message);
            } else {
                console.log("SERVER ACTION SUCCESS (listDatasets):", response);
                // Convert to plain object for client
                resolve(response);
            }
        });
    });
}

export async function setActiveDataset(filename: string) {
    return new Promise((resolve, reject) => {
        // @ts-ignore
        client.setActiveDataset({ filename }, (err: any) => {
            if (err) {
                reject(err.message);
            } else {
                revalidatePath('/', 'layout');
                resolve(true);
            }
        });
    });
}

export async function uploadDataset(formData: FormData) {
    console.log("SERVER ACTION: uploadDataset called");
    const file = formData.get('file') as File;
    if (!file) {
        console.error("SERVER ACTION: No file found in FormData");
        throw new Error("No file uploaded");
    }

    console.log(`Starting upload for ${file.name} (${file.size} bytes)`);

    return new Promise((resolve, reject) => {
        try {
            // @ts-ignore
            console.log("SERVER ACTION: Initiating gRPC call...");
            const call = client.uploadDataset((err: any, response: any) => {
                if (err) {
                    console.error("SERVER ACTION: gRPC Callback Error:", err);
                    reject(err.message);
                } else {
                    console.log("SERVER ACTION: gRPC Success:", response);
                    revalidatePath('/', 'layout');
                    resolve(response);
                }
            });

            call.on('status', (status: any) => {
                console.log("SERVER ACTION: Stream Status:", status);
            });

            call.on('error', (err: any) => {
                console.error("SERVER ACTION: Stream Error event:", err);
            });

            // 1. Send Filename
            console.log("SERVER ACTION: Writing filename...");
            // @ts-ignore
            call.write({ filename: file.name });

            // 2. Stream chunks
            const chunkSize = 64 * 1024; // 64KB
            const stream = file.stream();
            const reader = stream.getReader();

            async function read() {
                try {
                    let { done, value } = await reader.read();
                    if (done) {
                        console.log("SERVER ACTION: Finished reading file. Ending stream.");
                        call.end();
                        return;
                    }

                    // value is Uint8Array
                    // @ts-ignore
                    // console.log(`SERVER ACTION: Writing chunk (${value.length} bytes)`);
                    call.write({ chunk: Buffer.from(value) });
                    await read();
                } catch (readErr) {
                    console.error("SERVER ACTION: Error reading/writing stream:", readErr);
                    call.end();
                    reject(readErr);
                }
            }

            read().catch(e => {
                console.error("Stream reading error wrapper:", e);
                call.end();
                reject(e.message);
            });
        } catch (setupErr: any) {
            console.error("SERVER ACTION: Setup Error:", setupErr);
            reject(setupErr.message);
        }
    });
}


