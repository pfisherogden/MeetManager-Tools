import * as admin from "firebase-admin";

const initAdmin = () => {
	if (admin.apps.length === 0) {
		admin.initializeApp({
			credential: admin.credential.applicationDefault(),
			projectId:
				process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "mmtools-488404",
		});
	}
	return admin.firestore();
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
