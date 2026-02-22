import { getApps, initializeApp } from "firebase/app";
import { GoogleAuthProvider, getAuth } from "firebase/auth";

// Replace these with your project's configuration
const firebaseConfig = {
	apiKey: "PLACEHOLDER",
	authDomain: "PLACEHOLDER.firebaseapp.com",
	projectId: "PLACEHOLDER",
	storageBucket: "PLACEHOLDER.firebasestorage.app",
	messagingSenderId: "PLACEHOLDER",
	appId: "PLACEHOLDER",
};

// Initialize Firebase
const app =
	getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
