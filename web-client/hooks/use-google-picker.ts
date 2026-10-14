"use client";

import Cookies from "js-cookie";
import { useCallback, useEffect, useState } from "react";
import { getGoogleConfig } from "@/app/actions";

declare global {
	interface Window {
		gapi: any;
		google: any;
	}
}

export interface GoogleDriveFile {
	id: string;
	name: string;
	mimeType: string;
	sizeBytes: number;
	accessToken?: string;
	contentBase64?: string;
}

interface UseGooglePickerProps {
	onFileSelect: (file: GoogleDriveFile) => void;
	accessToken?: string | null;
}

export function useGooglePicker({
	onFileSelect,
	accessToken,
}: UseGooglePickerProps) {
	const [isLoaded, setIsLoaded] = useState(false);
	const [apiKey, setApiKey] = useState<string | null>(() => {
		const envKey =
			process.env.NEXT_PUBLIC_GOOGLE_API_KEY ||
			process.env.NEXT_PUBLIC_FIREBASE_API_KEY;
		return envKey && envKey !== "PLACEHOLDER" ? envKey : null;
	});
	const [appId, setAppId] = useState<string | null>(
		process.env.NEXT_PUBLIC_GOOGLE_APP_ID ||
			process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID ||
			"39869978853",
	);

	useEffect(() => {
		async function fetchConfig() {
			try {
				const config = await getGoogleConfig();
				if (config) {
					if (config.apiKey && config.apiKey !== "PLACEHOLDER") {
						setApiKey(config.apiKey);
					}
					if (config.appId) {
						setAppId(config.appId);
					}
				}
			} catch (err) {
				console.error("Failed to load Google Picker config:", err);
			}
		}
		fetchConfig();
	}, []);

	useEffect(() => {
		if (typeof window === "undefined") return;

		if (window.google?.picker) {
			setIsLoaded(true);
			return;
		}

		if (window.gapi?.load) {
			window.gapi.load("picker", () => setIsLoaded(true));
			return;
		}

		const existingScript = document.querySelector<HTMLScriptElement>(
			'script[src="https://apis.google.com/js/api.js"]',
		);
		const handleLoad = () => {
			if (window.gapi?.load) {
				window.gapi.load("picker", () => setIsLoaded(true));
			}
		};

		if (existingScript) {
			existingScript.addEventListener("load", handleLoad);
		} else {
			const script = document.createElement("script");
			script.src = "https://apis.google.com/js/api.js";
			script.async = true;
			script.onload = handleLoad;
			document.body.appendChild(script);
		}

		const existingGsi = document.querySelector<HTMLScriptElement>(
			'script[src="https://accounts.google.com/gsi/client"]',
		);
		if (!existingGsi) {
			const gsiScript = document.createElement("script");
			gsiScript.src = "https://accounts.google.com/gsi/client";
			gsiScript.async = true;
			document.body.appendChild(gsiScript);
		}

		return () => {
			if (existingScript) {
				existingScript.removeEventListener("load", handleLoad);
			}
		};
	}, []);

	const openPicker = useCallback(async () => {
		if (
			!isLoaded &&
			!(typeof window !== "undefined" && window.google?.picker)
		) {
			console.error("Google Picker script not loaded");
			return;
		}

		let currentToken =
			accessToken ||
			Cookies.get("googleAccessToken") ||
			(typeof window !== "undefined"
				? (window as any).__MM_TEST_GOOGLE_TOKEN__
				: null) ||
			null;

		if (!currentToken) {
			try {
				const { auth, googleProvider } = await import("@/lib/firebase");
				const { signInWithPopup, GoogleAuthProvider } = await import(
					"firebase/auth"
				);
				const result = await signInWithPopup(auth, googleProvider);
				const credential = GoogleAuthProvider.credentialFromResult(result);
				currentToken = credential?.accessToken || null;
				if (currentToken) {
					const isSecure =
						typeof window !== "undefined" &&
						window.location.protocol === "https:";
					Cookies.set("googleAccessToken", currentToken, {
						expires: 1 / 24,
						secure: isSecure,
						sameSite: "strict",
						path: "/",
					});
				}
			} catch (err) {
				console.error("Failed to authenticate with Google:", err);
				const { toast } = await import("sonner");
				toast.error("Google authentication failed");
				return;
			}
		}

		if (!currentToken) {
			console.error("No access token available after authentication");
			const { toast } = await import("sonner");
			toast.error("No Google access token available");
			return;
		}

		console.log("[Google Picker Debug] Initializing with:", {
			hasAccessToken: !!currentToken,
			appId: appId,
			origin: typeof window !== "undefined" ? window.location.origin : null,
			apiKeyPrefix: apiKey ? `${apiKey.substring(0, 8)}...` : "none",
			apiKeyLength: apiKey?.length || 0,
		});

		let view: any = window.google.picker.ViewId?.DOCS || "all";
		if (typeof window.google.picker.DocsView === "function") {
			const docsView = new window.google.picker.DocsView();
			if (typeof docsView.setIncludeFolders === "function") {
				docsView.setIncludeFolders(true);
			}
			if (typeof docsView.setSelectFolderEnabled === "function") {
				docsView.setSelectFolderEnabled(false);
			}
			view = docsView;
		}

		let builder = new window.google.picker.PickerBuilder()
			.addView(view)
			.setOAuthToken(currentToken);

		if (
			apiKey &&
			apiKey !== "PLACEHOLDER" &&
			typeof builder.setDeveloperKey === "function"
		) {
			builder = builder.setDeveloperKey(apiKey) || builder;
		}

		if (appId && typeof builder.setAppId === "function") {
			builder = builder.setAppId(appId) || builder;
		}

		// setOrigin is critical if the API key has HTTP referrer restrictions,
		// but must only be set on standard http/https origins (not tauri://)
		if (
			typeof window !== "undefined" &&
			(window.location.protocol === "http:" ||
				window.location.protocol === "https:") &&
			typeof builder.setOrigin === "function"
		) {
			builder = builder.setOrigin(window.location.origin) || builder;
		}

		const picker = (
			builder.setCallback((data: any) => {
				if (data.action === window.google.picker.Action.PICKED) {
					const doc = data.docs[0];
					onFileSelect({
						id: doc.id,
						name: doc.name,
						mimeType: doc.mimeType,
						sizeBytes: doc.sizeBytes,
						accessToken: currentToken || undefined,
					});
				}
			}) || builder
		).build();

		picker.setVisible(true);
	}, [isLoaded, accessToken, apiKey, appId, onFileSelect]);

	return { openPicker, isLoaded };
}
