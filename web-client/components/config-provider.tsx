"use client";

import type React from "react";
import { createContext, useContext, useEffect, useState } from "react";
import { getAdminConfig } from "@/app/actions";

interface AdminConfig {
	meetName: string;
	meetDescription: string;
}

const ConfigContext = createContext<AdminConfig>({
	meetName: "",
	meetDescription: "",
});

export const useConfig = () => useContext(ConfigContext);

export function ConfigProvider({ children }: { children: React.ReactNode }) {
	const [config, setConfig] = useState<AdminConfig>({
		meetName: "",
		meetDescription: "",
	});

	useEffect(() => {
		getAdminConfig()
			.then((res: any) => {
				if (res) {
					setConfig({
						meetName: res.meetName || "",
						meetDescription: res.meetDescription || "",
					});
				}
			})
			.catch((err) => console.error("Failed to load config", err));
	}, []);

	// We can expose a refresh function if needed, but for now revalidatePath in action handles page reloads.
	// However, client-side context won't auto-update unless we trigger it.
	// For now, assume reload on update is fine.

	return (
		<ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>
	);
}
