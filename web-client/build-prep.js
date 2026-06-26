// build-prep.js
const fs = require("node:fs");
const path = require("node:path");

const isStatic = process.env.EXPORT_STATIC === "true";
if (!isStatic) {
	console.log("Not a static export build. Skipping prep.");
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
			'export const dynamic = "force-dynamic";',
			'export const dynamic = "force-static";',
		);
		fs.writeFileSync(filepath, content, "utf8");
		console.log(`Prepped: ${page} -> force-static`);
	} else {
		console.warn(`File not found during prep: ${filepath}`);
	}
}
