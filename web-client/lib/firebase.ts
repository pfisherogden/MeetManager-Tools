import { getApps, initializeApp } from "firebase/app";
import { GoogleAuthProvider, getAuth } from "firebase/auth";

// Firebase configuration using environment variables
// Note: NEXT_PUBLIC_ prefix is required for client-side access in Next.js
const firebaseConfig = {
	apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "PLACEHOLDER",
	authDomain:
		process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ||
		"mmtools-488404.firebaseapp.com",
	projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "mmtools-488404",
	storageBucket:
		process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET ||
		"mmtools-488404.firebasestorage.app",
	messagingSenderId:
		process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "39869978853",
	appId:
		process.env.NEXT_PUBLIC_FIREBASE_APP_ID ||
		"1:39869978853:web:7966328ddf7f3dc071dc0c",
	measurementId:
		process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || "G-KDE7ZPS0X5",
};

// Initialize Firebase
export const app =
	getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
googleProvider.addScope("https://www.googleapis.com/auth/drive.file");
