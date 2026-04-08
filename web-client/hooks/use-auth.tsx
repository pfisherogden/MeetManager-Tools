"use client";

import {
	GoogleAuthProvider,
	getIdToken,
	onAuthStateChanged,
	signInWithPopup,
	signOut,
	type User,
	type UserCredential,
} from "firebase/auth";
import Cookies from "js-cookie";
import {
	createContext,
	type ReactNode,
	useContext,
	useEffect,
	useState,
} from "react";
import { auth, googleProvider } from "@/lib/firebase";

interface AuthContextType {
	user: User | null;
	googleAccessToken: string | null;
	loading: boolean;
	login: () => Promise<UserCredential>;
	logout: () => Promise<void>;
	getToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<User | null>(null);
	const [googleAccessToken, setGoogleAccessToken] = useState<string | null>(
		null,
	);
	const [loading, setLoading] = useState(true);

	const isAuthDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === "true";

	useEffect(() => {
		const token = Cookies.get("googleAccessToken");
		if (token) setGoogleAccessToken(token);

		if (isAuthDisabled) {
			// Mock local user
			const mockUser = {
				uid: "dev-user",
				email: "dev@local.host",
				displayName: "Local Developer",
			} as User;
			setUser(mockUser);
			Cookies.set("idToken", "dev-token", {
				expires: 1 / 24,
				secure: false, // Local dev usually not https
				sameSite: "strict",
			});
			Cookies.set("x-user-id", mockUser.uid, {
				expires: 1 / 24,
				secure: false,
				sameSite: "strict",
			});
			setLoading(false);
			return;
		}

		const unsubscribe = onAuthStateChanged(auth, async (user) => {
			setUser(user);
			if (user) {
				const token = await getIdToken(user);
				Cookies.set("idToken", token, {
					expires: 1 / 24,
					secure: true,
					sameSite: "strict",
				});
				Cookies.set("x-user-id", user.uid, {
					expires: 1 / 24,
					secure: true,
					sameSite: "strict",
				});
			} else {
				Cookies.remove("idToken");
				Cookies.remove("x-user-id");
				Cookies.remove("googleAccessToken");
				setGoogleAccessToken(null);
			}
			setLoading(false);
		});
		return () => unsubscribe();
	}, [isAuthDisabled]);

	const login = async () => {
		if (isAuthDisabled) return {} as UserCredential;
		const result = await signInWithPopup(auth, googleProvider);
		const credential = GoogleAuthProvider.credentialFromResult(result);
		if (credential?.accessToken) {
			setGoogleAccessToken(credential.accessToken);
			Cookies.set("googleAccessToken", credential.accessToken, {
				expires: 1 / 24,
				secure: true,
				sameSite: "strict",
			});
		}
		return result;
	};

	const logout = async () => {
		Cookies.remove("idToken");
		Cookies.remove("x-user-id");
		Cookies.remove("googleAccessToken");
		setGoogleAccessToken(null);
		if (isAuthDisabled) {
			setUser(null);
			return;
		}
		return signOut(auth);
	};

	const getToken = async () => {
		if (isAuthDisabled) return "dev-token";
		if (!user) return null;
		return getIdToken(user);
	};

	return (
		<AuthContext.Provider
			value={{ user, googleAccessToken, loading, login, logout, getToken }}
		>
			{children}
		</AuthContext.Provider>
	);
}

export function useAuth() {
	const context = useContext(AuthContext);
	if (context === undefined) {
		throw new Error("useAuth must be used within an AuthProvider");
	}
	return context;
}
