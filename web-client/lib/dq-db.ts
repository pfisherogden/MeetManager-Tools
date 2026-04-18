import * as fs from "node:fs";
import * as admin from "firebase-admin";

// File-based mock for local/CI development when Firestore is unavailable
// This allows sharing data across processes (e.g. API route vs Server Action)
class MockFirestore {
	private getFilePath(): string {
		const path = process.env.FIRESTORE_MOCK_PATH || "/tmp/mock_firestore.json";
		if (Math.random() < 0.01) { // Throttle path logging
			console.log(`MockFirestore: Using file path: ${path}`);
		}
		return path;
	}

	private readStorage(): Map<string, any> {
		const filePath = this.getFilePath();
		try {
			if (fs.existsSync(filePath)) {
				const content = fs.readFileSync(filePath, "utf8");
				console.log(`MockFirestore READ: ${content.length} bytes from ${filePath}`);
				const data = JSON.parse(content);
				return new Map(Object.entries(data));
			} else {
				console.log(`MockFirestore READ: File does not exist at ${filePath}`);
			}
		} catch (e: any) {
			console.error(`MockFirestore READ ERROR: ${filePath}: ${e.message}`);
		}
		return new Map<string, any>();
	}

	private writeStorage(storage: Map<string, any>) {
		const filePath = this.getFilePath();
		try {
			// Ensure directory exists
			const dir = fs.realpathSync(require("node:path").dirname(filePath));
			console.log(`MockFirestore WRITE: Directory ${dir} is writable`);

			const data = Object.fromEntries(storage);
			const content = JSON.stringify(data, null, 2);
			fs.writeFileSync(filePath, content, "utf8");
			console.log(`MockFirestore WRITE SUCCESS: ${content.length} bytes to ${filePath}`);
		} catch (e: any) {
			console.error(`MockFirestore WRITE ERROR: ${filePath}: ${e.message}`);
			// Fallback to a guaranteed writable location if possible
			try {
				const fallback = "/tmp/mock_firestore_fallback.json";
				fs.writeFileSync(fallback, JSON.stringify(Object.fromEntries(storage)));
				console.log(`MockFirestore: Wrote to fallback ${fallback}`);
			} catch (e2) {}
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
	console.log(
		`initAdmin: mockDb=${!!mockDb}, USE_MOCK=${process.env.USE_MOCK_FIRESTORE}`,
	);
	if (mockDb) return mockDb as any;

	if (process.env.USE_MOCK_FIRESTORE === "true") {
		console.log("USE_MOCK_FIRESTORE is true, using in-memory mock");
		mockDb = new MockFirestore();
		return mockDb as any;
	}

	try {
		console.log("initAdmin: Attempting real Firestore initialization...");
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
		console.warn("Firestore initialization failed, using in-memory mock:", e);
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

export async function saveDq(
	clientDqId: string,
	dqDetails: any,
): Promise<void> {
	if (!clientDqId) throw new Error("clientDqId is required");

	try {
		const db = initAdmin();
		const dqRef = db.collection("disqualifications").doc(clientDqId);

		await dqRef.set({
			...dqDetails,
			createdAt: new Date().toISOString(),
		});
		console.log(`FIRESTORE: Saved DQ ${clientDqId}`);
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

		return snapshot.docs.map((doc) => ({
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
