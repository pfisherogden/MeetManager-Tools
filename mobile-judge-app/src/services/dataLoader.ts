import { Linking, Platform } from "react-native";
import { loadFromJSON } from "../database/db";

const ALLOWED_HOSTS = [
	"localhost",
	"127.0.0.1",
	"frontend",
	"pfisherogden.github.io",
	"storage.googleapis.com",
	"mmtools-frontend-ckhcthqhya-uw.a.run.app",
	"example.com", // For testing
];

const validateUrl = (url: string): boolean => {
	try {
		// Use regex to extract hostname safely (stripping port if present)
		const match = url.match(/^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/\n?]+)/im);
		let hostname = match ? match[1] : "";
		// Strip port if present
		if (hostname.includes(":")) {
			hostname = hostname.split(":")[0];
		}
		return ALLOWED_HOSTS.includes(hostname.toLowerCase()) || hostname.endsWith(".run.app");
	} catch (e) {
		console.warn(`Invalid URL format: ${url}`);
		return false;
	}
};

const parseQueryParams = (url: string) => {
	const queryParams: Record<string, string> = {};
	if (!url) return queryParams;

	try {
		const searchPart = url.split("?")[1];
		if (!searchPart) return queryParams;

		// Use a more robust regex-based approach to extract known parameters that might be URLs
		// This handles the case where nested URLs contain their own query parameters
		const params = ["program_url", "dq_url", "sync_url", "token", "uid"];

		for (const param of params) {
			const regex = new RegExp(`[?&]${param}=([^&]+)`);
			const match = url.match(regex);
			if (match) {
				queryParams[param] = decodeURIComponent(match[1]);
			}
		}
	} catch (e) {
		console.warn("Error parsing query params:", e);
	}

	return queryParams;
};

export const loadDataFromUrl = async () => {
	let url = "";

	if (Platform.OS === "web") {
		url = window.location.href;
	} else {
		const initialUrl = await Linking.getInitialURL();
		url = initialUrl || "";
	}

	const queryParams = parseQueryParams(url);

	const programUrl = queryParams.program_url;
	const dqUrl = queryParams.dq_url;
	const syncUrl = queryParams.sync_url;

	let loaded = false;
	let dqData = null;
	let errorMessage = "";

	if (programUrl) {
		if (validateUrl(programUrl)) {
			try {
				console.log(`FETCHING PROGRAM DATA FROM: ${programUrl}`);
				const response = await fetch(programUrl as string);
				console.log(`FETCH STATUS: ${response.status}`);
				if (!response.ok) throw new Error(`Server returned ${response.status}`);
				const data = await response.json();
				console.log(`FETCH SUCCESS: ${Object.keys(data).length} keys`);

				// Structure validation: must contain 'sessions' or 'events'
				if (data && (data.sessions || data.events)) {
					loadFromJSON(data);
					loaded = true;
				} else {
					errorMessage = "Invalid program data structure from URL";
					console.error(errorMessage);
				}
			} catch (e: any) {
				errorMessage = `Failed to fetch program data: ${e.message}`;
				console.error(errorMessage);
			}
		} else {
			errorMessage = `Blocked untrusted program URL: ${programUrl}`;
			console.warn(errorMessage);
		}
	}

	if (dqUrl) {
		if (validateUrl(dqUrl)) {
			try {
				const response = await fetch(dqUrl as string);
				if (!response.ok) throw new Error(`Server returned ${response.status}`);
				const data = await response.json();

				// Structure validation: must be an object (map of category to DqCode[])
				if (data && typeof data === "object" && !Array.isArray(data)) {
					dqData = data;
				} else {
					console.error("Invalid DQ data structure: expected object");
				}
			} catch (e) {
				console.error("Error loading DQ data:", e);
			}
		} else {
			console.warn(`Blocked untrusted DQ URL: ${dqUrl}`);
		}
	}

	return { loaded, dqData, syncUrl, errorMessage };
	};
