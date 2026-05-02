import * as fs from "node:fs";
import * as admin from "firebase-admin";

// File-based mock for local/CI development when Firestore is unavailable.
// This version supports per-user isolation to prevent E2E test collisions.
class MockFirestore {
	private readonly userId: string | null;

	constructor(userId: string | null = null) {
		this.userId = userId;
	}

	private getFilePath(): string {
		const basepath =
			process.env.FIRESTORE_MOCK_PATH || "/app/tmp/mock_firestore.json";
		if (this.userId) {
			const dir = basepath.substring(0, basepath.lastIndexOf("/"));
			return `${dir}/mock_firestore_${this.userId}.json`;
		}
		return basepath;
	}

	private async readStorage(): Promise<Map<string, any>> {
		const filePath = this.getFilePath();
		// No logging in read to reduce noise
		let attempts = 0;
		while (attempts < 5) {
			try {
				if (!fs.existsSync(filePath)) {
					return new Map<string, any>();
				}
				const realPath = fs.realpathSync(filePath);
				const content = fs.readFileSync(realPath, "utf8");
				if (content.trim() === "") {
					return new Map<string, any>();
				}
				const data = JSON.parse(content);
				return new Map(Object.entries(data));
			} catch (_e: any) {
				// console.error(`MockFirestore READ ERROR: ${filePath}: ${e.message}`);
			}
			attempts++;
			if (attempts < 5) {
				await new Promise((resolve) => setTimeout(resolve, 200));
			}
		}
		return new Map<string, any>();
	}

	private async writeStorage(storage: Map<string, any>) {
		const filePath = this.getFilePath();
		// console.log(`MockFirestore: WRITING to ${filePath}`);
		try {
			const dir = filePath.substring(0, filePath.lastIndexOf("/"));
			if (dir && !fs.existsSync(dir)) {
				fs.mkdirSync(dir, { recursive: true });
			}

			const data = Object.fromEntries(storage);
			const content = JSON.stringify(data, null, 2);

			const tempPath = `${filePath}.tmp.${Date.now()}`;
			const fd = fs.openSync(tempPath, "w");
			fs.writeSync(fd, content);
			fs.fsyncSync(fd);
			fs.closeSync(fd);

			fs.renameSync(tempPath, filePath);
		} catch (e: any) {
			console.error(`MockFirestore WRITE ERROR: ${filePath}: ${e.message}`);
		}
	}

	collection(name: string) {
		return {
			doc: (id: string) => ({
				get: async () => {
					const storage = await this.readStorage();
					const key = `${name}/${id}`;
					return {
						exists: storage.has(key),
						data: () => storage.get(key),
					};
				},
				set: async (data: any) => {
					const storage = await this.readStorage();
					storage.set(`${name}/${id}`, data);
					await this.writeStorage(storage);
				},
			}),
			orderBy: () => ({
				get: async () => {
					const storage = await this.readStorage();
					const docs = Array.from(storage.entries())
						.filter(([key]) => key.startsWith(`${name}/`))
						.map(([key, value]) => ({
							id: key.split("/")[1],
							data: () => value,
						}));
					docs.sort((a, b) => {
						const dateA = a.data().createdAt || "";
						const dateB = b.data().createdAt || "";
						return dateB.localeCompare(dateA);
					});
					return { docs };
				},
			}),
		};
	}
}

const initAdmin = (userId?: string | null) => {
	if (process.env.USE_MOCK_FIRESTORE === "true") {
		// Return a new instance for each user context to ensure isolation
		return new MockFirestore(userId || "shared") as any;
	}

	try {
		if (admin.apps.length === 0) {
			const credential = admin.credential.applicationDefault();
			admin.initializeApp({
				credential,
				projectId:
					process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "mmtools-488404",
			});
		}
		return admin.firestore();
	} catch (e) {
		console.warn(
			"Firestore initialization failed, using file-based mock:",
			(e as Error).message,
		);
		return new MockFirestore(userId || "shared") as any;
	}
};

export function getDb(userId?: string | null) {
	return initAdmin(userId);
}

export async function checkDqExists(
	clientDqId: string,
	userId?: string | null,
): Promise<boolean> {
	if (!clientDqId) return false;

	try {
		const db = getDb(userId);
		const dqRef = db.collection("disqualifications").doc(clientDqId);
		const dqSnap = await dqRef.get();
		return dqSnap.exists;
	} catch (error: any) {
		console.error(`FIRESTORE ERROR (checkDqExists): ${error.message}`, {
			code: error.code,
			details: error.details,
		});
		throw error;
	}
}

export async function saveDq(
	clientDqId: string,
	data: any,
	userId?: string | null,
) {
	try {
		const db = getDb(userId);
		const dqRef = db.collection("disqualifications").doc(clientDqId);
		await dqRef.set({
			...data,
			createdAt: new Date().toISOString(),
		});
	} catch (error: any) {
		console.error(`FIRESTORE ERROR (saveDq): ${error.message}`, {
			code: error.code,
			details: error.details,
		});
		throw error;
	}
}

export async function getDqs(userId?: string | null): Promise<any[]> {
	try {
		const db = getDb(userId);
		const snapshot = await db
			.collection("disqualifications")
			.orderBy("createdAt", "desc")
			.get();
		return snapshot.docs.map((doc: any) => ({
			id: doc.id,
			...doc.data(),
		}));
	} catch (error: any) {
		console.error(`FIRESTORE ERROR (getDqs): ${error.message}`, {
			code: error.code,
			details: error.details,
		});
		throw error;
	}
}

export async function deleteDq(dqId: string, userId?: string | null) {
	try {
		const db = getDb(userId);
		if (process.env.USE_MOCK_FIRESTORE === "true") {
			const storage = await (db as any).readStorage();
			storage.delete(`disqualifications/${dqId}`);
			await (db as any).writeStorage(storage);
		} else {
			await db.collection("disqualifications").doc(dqId).delete();
		}
	} catch (error: any) {
		console.error(`FIRESTORE ERROR (deleteDq): ${error.message}`);
		throw error;
	}
}

export async function clearAllDqs(userId?: string | null) {
	try {
		const db = getDb(userId);
		if (process.env.USE_MOCK_FIRESTORE === "true") {
			const storage = await (db as any).readStorage();
			for (const key of storage.keys()) {
				if (key.startsWith("disqualifications/")) {
					storage.delete(key);
				}
			}
			await (db as any).writeStorage(storage);
		} else {
			const snapshot = await db.collection("disqualifications").get();
			const batch = db.batch();
			for (const doc of snapshot.docs) {
				batch.delete(doc.ref);
			}
			await batch.commit();
		}
	} catch (error: any) {
		console.error(`FIRESTORE ERROR (clearAllDqs): ${error.message}`);
		throw error;
	}
}
