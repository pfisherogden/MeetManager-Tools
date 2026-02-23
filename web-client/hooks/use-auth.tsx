"use client";

import {
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
	loading: boolean;
	login: () => Promise<UserCredential>;
	logout: () => Promise<void>;
	getToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<User | null>(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const unsubscribe = onAuthStateChanged(auth, async (user) => {
			setUser(user);
			if (user) {
				const token = await getIdToken(user);
				Cookies.set("idToken", token, {
					expires: 1 / 24,
					secure: true,
					sameSite: "strict",
				});
			} else {
				Cookies.remove("idToken");
			}
			setLoading(false);
		});
		return () => unsubscribe();
	}, []);

	const login = async () => {
		return signInWithPopup(auth, googleProvider);
	};

	const logout = async () => {
		Cookies.remove("idToken");
		return signOut(auth);
	};

	const getToken = async () => {
		if (!user) return null;
		return getIdToken(user);
	};

	return (
		<AuthContext.Provider value={{ user, loading, login, logout, getToken }}>
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
