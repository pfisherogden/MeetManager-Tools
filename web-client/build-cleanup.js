// build-cleanup.js
const fs = require("node:fs");
const path = require("node:path");

const isStatic = process.env.EXPORT_STATIC === "true";
if (!isStatic) {
	process.exit(0);
}

const pages = [
	"app/admin/page.tsx",
	"app/athletes/page.tsx",
	"app/dqs/page.tsx",
	"app/entries/page.tsx",
	"app/events/page.tsx",
	"app/meets/page.tsx",
	"app/page.tsx",
	"app/relays/page.tsx",
	"app/reports/page.tsx",
	"app/scores/page.tsx",
	"app/sessions/page.tsx",
	"app/teams/page.tsx",
];

for (const page of pages) {
	const filepath = path.join(__dirname, page);
	if (fs.existsSync(filepath)) {
		let content = fs.readFileSync(filepath, "utf8");
		content = content.replace(
			'export const dynamic = "force-static";',
			'export const dynamic = "force-dynamic";',
		);
		fs.writeFileSync(filepath, content, "utf8");
		console.log(`Cleaned up: ${page} -> force-dynamic`);
	}
}

// Restore actions import to server actions after static build
const actionsPath = path.join(__dirname, "app/actions.ts");
if (fs.existsSync(actionsPath)) {
	fs.writeFileSync(actionsPath, 'export * from "./actions.server";\n', "utf8");
	console.log("Cleaned up: app/actions.ts -> actions.server");
}
