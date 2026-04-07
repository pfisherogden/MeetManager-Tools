import * as admin from "firebase-admin";

const initAdmin = () => {
	if (admin.apps.length === 0) {
		admin.initializeApp({
			projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "mmtools-488404",
		});
	}
	return admin.firestore();
};

export async function checkDqExists(clientDqId: string): Promise<boolean> {
	if (!clientDqId) return false;

	const db = initAdmin();
	const dqRef = db.collection("disqualifications").doc(clientDqId);
	const dqSnap = await dqRef.get();

	return dqSnap.exists;
}

export async function saveDq(clientDqId: string, dqDetails: any): Promise<void> {
	if (!clientDqId) throw new Error("clientDqId is required");

	const db = initAdmin();
	const dqRef = db.collection("disqualifications").doc(clientDqId);

	await dqRef.set({
		...dqDetails,
		createdAt: new Date().toISOString(),
	});
}
