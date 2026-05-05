import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
	plugins: [react()],
	test: {
		environment: "jsdom",
		globals: true,
		setupFiles: [],
		exclude: ["**/node_modules/**", "**/dist/**", "**/tests-e2e/**"],
		alias: {
			"@": path.resolve(__dirname, "."),
		},
		pool: "forks",
	} as any,
	poolOptions: {
		forks: {
			singleFork: true,
		},
	},
});
