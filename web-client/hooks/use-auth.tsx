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
import { usePathname, useRouter } from "next/navigation";
import {
	createContext,
	type ReactNode,
	useCallback,
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
	const pathname = usePathname();
	const router = useRouter();

	const isAuthDisabled =
		process.env.NEXT_PUBLIC_AUTH_DISABLED === "true" ||
		process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS === "true";

	useEffect(() => {
		// Client-side redirection backup for protected routes
		if (!loading && !isAuthDisabled && !user) {
			const isPublicPath =
				pathname === "/login" ||
				pathname.startsWith("/judge") ||
				pathname.startsWith("/api/test") ||
				pathname.startsWith("/api/data");

			if (!isPublicPath) {
				if (process.env.NODE_ENV !== "production") {
					console.log(
						`[AuthProvider] Redirecting unauthenticated user from ${pathname} to /login`,
					);
				}
				router.push(`/login?returnUrl=${encodeURIComponent(pathname)}`);
			}
		}
	}, [user, loading, pathname, router, isAuthDisabled]);

	useEffect(() => {
		if (process.env.NODE_ENV !== "production") {
			console.log(
				`[AuthProvider] Init: isAuthDisabled=${isAuthDisabled}, bypass=${process.env.NEXT_PUBLIC_E2E_AUTH_BYPASS}`,
			);
		}
	}, [isAuthDisabled]);

	useEffect(() => {
		const token = Cookies.get("googleAccessToken");
		if (token) setGoogleAccessToken(token);

		if (isAuthDisabled) {
			// Mock local user for development or E2E testing
			// Prioritize the UID from cookies if set by the E2E test for isolation
			const storedUid = Cookies.get("x-user-id");
			const mockUid = storedUid || "e2e-default-user";

			if (process.env.NODE_ENV !== "production") {
				console.log(`[AuthProvider] E2E Bypass Active. UID: ${mockUid}`);
			}

			const mockUser = {
				uid: mockUid,
				email: "e2e@example.com",
				displayName: "E2E Test User",
			} as User;

			setUser(mockUser);

			// Ensure cookies are set for gRPC consistent routing
			if (typeof window !== "undefined") {
				localStorage.setItem("x-user-id", mockUid);
			}
			if (!storedUid) {
				Cookies.set("x-user-id", mockUid, {
					path: "/",
					sameSite: "strict",
					secure: process.env.NODE_ENV === "production",
				});
			}

			// In bypass mode, we also need a dummy idToken for the middleware
			if (!Cookies.get("idToken")) {
				Cookies.set("idToken", "dev-token", {
					path: "/",
					sameSite: "strict",
					secure: process.env.NODE_ENV === "production",
				});
			}

			setLoading(false);
			return;
		}

		const unsubscribe = onAuthStateChanged(auth, async (user) => {
			setUser(user);
			if (user) {
				const idToken = await getIdToken(user);
				if (typeof window !== "undefined") {
					localStorage.setItem("x-user-id", user.uid);
				}
				Cookies.set("idToken", idToken, {
					expires: 1 / 24, // 1 hour
					secure: true,
					sameSite: "strict",
					path: "/",
				});
				Cookies.set("x-user-id", user.uid, {
					expires: 1 / 24,
					secure: true,
					sameSite: "strict",
					path: "/",
				});
			} else {
				if (typeof window !== "undefined") {
					localStorage.removeItem("x-user-id");
				}
				Cookies.remove("idToken", { path: "/" });
				Cookies.remove("x-user-id", { path: "/" });
				Cookies.remove("googleAccessToken", { path: "/" });
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
				path: "/",
			});
		}
		return result;
	};

	const logout = useCallback(async () => {
		try {
			if (!isAuthDisabled) {
				await signOut(auth);
			}
			if (typeof window !== "undefined") {
				localStorage.removeItem("x-user-id");
			}
			Cookies.remove("idToken", { path: "/" });
			Cookies.remove("x-user-id", { path: "/" });
			Cookies.remove("googleAccessToken", { path: "/" });
			setUser(null);
			setGoogleAccessToken(null);
			router.push("/login");
		} catch (error) {
			console.error("Logout error", error);
		}
	}, [router, isAuthDisabled]);

	const getToken = useCallback(async () => {
		if (isAuthDisabled) return "dev-token";
		if (!user) return null;
		return await getIdToken(user);
	}, [user, isAuthDisabled]);

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
