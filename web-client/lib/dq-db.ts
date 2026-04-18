import * as fs from "node:fs";
import * as admin from "firebase-admin";

// File-based mock for local/CI development when Firestore is unavailable
// This allows sharing data across processes (e.g. API route vs Server Action)
class MockFirestore {
	private getFilePath(): string {
		return process.env.FIRESTORE_MOCK_PATH || "/tmp/mock_firestore.json";
	}

	private readStorage(): Map<string, any> {
		const filePath = this.getFilePath();
		let attempts = 0;
		while (attempts < 3) {
			try {
				if (fs.existsSync(filePath)) {
					const realPath = fs.realpathSync(filePath);
					const content = fs.readFileSync(realPath, "utf8");
					const data = JSON.parse(content);
					return new Map(Object.entries(data));
				}
			} catch (e: any) {
				console.error(`MockFirestore READ ERROR: ${filePath}: ${e.message}`);
			}
			attempts++;
			if (attempts < 3) {
				// Wait 500ms before retry
				const start = Date.now();
				while (Date.now() - start < 500) {}
			}
		}
		return new Map<string, any>();
	}

	private writeStorage(storage: Map<string, any>) {
		const filePath = this.getFilePath();
		try {
			const data = Object.fromEntries(storage);
			const content = JSON.stringify(data, null, 2);

			// Use more robust write with sync
			const fd = fs.openSync(filePath, "w");
			fs.writeSync(fd, content);
			fs.fsyncSync(fd);
			fs.closeSync(fd);
		} catch (e: any) {
			console.error(`MockFirestore WRITE ERROR: ${filePath}: ${e.message}`);
		}
	}

	collection(name: string) {
		return {
			doc: (id: string) => ({
				get: async () => {
					const storage = this.readStorage();
					const key = `${name}/${id}`;
					return {
						exists: storage.has(key),
						data: () => storage.get(key),
					};
				},
				set: async (data: any) => {
					const storage = this.readStorage();
					storage.set(`${name}/${id}`, data);
					this.writeStorage(storage);
				},
			}),
			orderBy: () => ({
				get: async () => {
					const storage = this.readStorage();
					const docs = Array.from(storage.entries())
						.filter(([key]) => key.startsWith(`${name}/`))
						.map(([key, value]) => ({
							id: key.split("/")[1],
							data: () => value,
						}));
					// Simplified sorting by createdAt if it exists in data
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

let mockDb: MockFirestore | null = null;

const initAdmin = () => {
	if (mockDb) return mockDb as any;

	if (process.env.USE_MOCK_FIRESTORE === "true") {
		console.log("USE_MOCK_FIRESTORE is true, using file-based mock");
		mockDb = new MockFirestore();
		return mockDb as any;
	}

	try {
		if (admin.apps.length === 0) {
			// Try to get credentials, if this fails it will throw
			const credential = admin.credential.applicationDefault();
			admin.initializeApp({
				credential,
				projectId:
					process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "mmtools-488404",
			});
		}
		return admin.firestore();
	} catch (e) {
		console.warn("Firestore initialization failed, using file-based mock:", e);
		if (!mockDb) mockDb = new MockFirestore();
		return mockDb as any;
	}
};

export async function checkDqExists(clientDqId: string): Promise<boolean> {
	if (!clientDqId) return false;

	try {
		const db = initAdmin();
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

export async function saveDq(clientDqId: string, data: any) {
	try {
		const db = initAdmin();
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

export async function getDqs(): Promise<any[]> {
	try {
		const db = initAdmin();
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
