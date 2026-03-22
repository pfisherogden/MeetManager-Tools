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

	const apiKey = process.env.NEXT_PUBLIC_GOOGLE_API_KEY;
	const _appId = process.env.NEXT_PUBLIC_GOOGLE_APP_ID; // Optional

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

	const openPicker = useCallback(() => {
		if (!isLoaded || !accessToken) {
			console.error("Picker not loaded or no access token");
			return;
		}

		const picker = new window.google.picker.PickerBuilder()
			.addView(window.google.picker.ViewId.DOCS)
			.setOAuthToken(accessToken)
			.setDeveloperKey(apiKey)
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
	}, [isLoaded, accessToken, apiKey, onFileSelect]);

	return { openPicker, isLoaded: isLoaded && !!accessToken };
}
