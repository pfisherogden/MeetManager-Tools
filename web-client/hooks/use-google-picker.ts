"use client";

import { useCallback, useEffect, useState } from "react";

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
}

interface UseGooglePickerProps {
	onFileSelect: (file: GoogleDriveFile) => void;
	accessToken: string | null;
}

export function useGooglePicker({
	onFileSelect,
	accessToken,
}: UseGooglePickerProps) {
	const [isLoaded, setIsLoaded] = useState(false);
	const [apiKey, setApiKey] = useState<string | null>(null);
	const [appId, setAppId] = useState<string | null>(null);

	useEffect(() => {
		async function fetchConfig() {
			try {
				const { getGoogleConfig } = await import("@/app/actions");
				const config = await getGoogleConfig();
				setApiKey(config.apiKey);
				setAppId(config.appId);
			} catch (err) {
				console.error("Failed to load Google Picker config:", err);
			}
		}
		fetchConfig();
	}, []);

	useEffect(() => {
		// Load GAPI
		const script = document.createElement("script");
		script.src = "https://apis.google.com/js/api.js";
		script.onload = () => {
			window.gapi.load("picker", () => setIsLoaded(true));
		};
		document.body.appendChild(script);

		// Load GSI (for newer auth if needed, though we use Firebase token)
		const gsiScript = document.createElement("script");
		gsiScript.src = "https://accounts.google.com/gsi/client";
		document.body.appendChild(gsiScript);

		return () => {
			document.body.removeChild(script);
			document.body.removeChild(gsiScript);
		};
	}, []);

	const openPicker = useCallback(async () => {
		if (!isLoaded || !apiKey) {
			console.error("Picker not loaded or API key missing");
			return;
		}

		let currentToken = accessToken;

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
					const Cookies = (await import("js-cookie")).default;
					Cookies.set("googleAccessToken", currentToken, {
						expires: 1 / 24,
						secure: true,
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
			return;
		}

		console.log("[Google Picker Debug] Initializing with:", {
			hasAccessToken: !!currentToken,
			appId: appId,
			origin: typeof window !== "undefined" ? window.location.origin : null,
			apiKeyPrefix: apiKey ? `${apiKey.substring(0, 8)}...` : "none",
			apiKeyLength: apiKey?.length || 0,
		});

		const builder = new window.google.picker.PickerBuilder()
			.addView(window.google.picker.ViewId.DOCS)
			.setOAuthToken(currentToken)
			.setDeveloperKey(apiKey);

		if (appId) {
			builder.setAppId(appId);
		}

		// setOrigin is critical if the API key has domain restrictions
		if (typeof window !== "undefined") {
			builder.setOrigin(window.location.origin);
		}

		const picker = builder
			.setCallback((data: any) => {
				if (data.action === window.google.picker.Action.PICKED) {
					const doc = data.docs[0];
					onFileSelect({
						id: doc.id,
						name: doc.name,
						mimeType: doc.mimeType,
						sizeBytes: doc.sizeBytes,
					});
				}
			})
			.build();

		picker.setVisible(true);
	}, [isLoaded, accessToken, apiKey, appId, onFileSelect]);

	return { openPicker, isLoaded: isLoaded && !!apiKey };
}
