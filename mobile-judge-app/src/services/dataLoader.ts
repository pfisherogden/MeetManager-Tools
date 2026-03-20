import { Linking, Platform } from "react-native";
import { loadFromJSON } from "../database/db";

const ALLOWED_HOSTS = [
	"localhost",
	"127.0.0.1",
	"pfisherogden.github.io",
	"example.com", // For testing
];

const validateUrl = (url: string): boolean => {
	try {
		// Use regex to extract hostname safely
		const match = url.match(/^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/\n?]+)/im);
		const hostname = match ? match[1] : "";
		return ALLOWED_HOSTS.includes(hostname.toLowerCase());
	} catch (e) {
		console.warn(`Invalid URL format: ${url}`);
		return false;
	}
};

const parseQueryParams = (url: string) => {
	const queryParams: Record<string, string> = {};
	if (!url) return queryParams;

	const queryString = url.split("?")[1];
	if (!queryString) return queryParams;

	queryString.split("&").forEach((param) => {
		const [key, value] = param.split("=");
		if (key) {
			queryParams[key] = decodeURIComponent(value || "");
		}
	});

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

	if (programUrl) {
		if (validateUrl(programUrl)) {
			try {
				const response = await fetch(programUrl as string);
				if (!response.ok) throw new Error("Failed to fetch program data");
				const data = await response.json();

				// Structure validation: must contain 'sessions' or 'events'
				if (data && (data.sessions || data.events)) {
					loadFromJSON(data);
					loaded = true;
				} else {
					console.error("Invalid program data structure");
				}
			} catch (e) {
				console.error("Error loading program data:", e);
			}
		} else {
			console.warn(`Blocked untrusted program URL: ${programUrl}`);
		}
	}

	if (dqUrl) {
		if (validateUrl(dqUrl)) {
			try {
				const response = await fetch(dqUrl as string);
				if (!response.ok) throw new Error("Failed to fetch DQ data");
				const data = await response.json();

				// Structure validation: must be an array
				if (Array.isArray(data)) {
					dqData = data;
				} else {
					console.error("Invalid DQ data structure: expected array");
				}
			} catch (e) {
				console.error("Error loading DQ data:", e);
			}
		} else {
			console.warn(`Blocked untrusted DQ URL: ${dqUrl}`);
		}
	}

	return { loaded, dqData, syncUrl };
};
