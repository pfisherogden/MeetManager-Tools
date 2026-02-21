import { Linking, Platform } from "react-native";
import { loadFromJSON } from "../database/db";

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
		try {
			const response = await fetch(programUrl as string);
			if (!response.ok) throw new Error("Failed to fetch program data");
			const data = await response.json();
			loadFromJSON(data);
			loaded = true;
		} catch (e) {
			console.error("Error loading program data:", e);
		}
	}

	if (dqUrl) {
		try {
			const response = await fetch(dqUrl as string);
			if (!response.ok) throw new Error("Failed to fetch DQ data");
			dqData = await response.json();
		} catch (e) {
			console.error("Error loading DQ data:", e);
		}
	}

	return { loaded, dqData, syncUrl };
};
