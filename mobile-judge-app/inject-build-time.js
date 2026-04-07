const fs = require("node:fs");
const path = require("node:path");

const appTsxPath = path.join(__dirname, "App.tsx");

let content = fs.readFileSync(appTsxPath, "utf8");

const now = new Date();
const formattedTime = `${now.toLocaleString("en-US", {
	timeZone: "America/Los_Angeles",
	year: "numeric",
	month: "2-digit",
	day: "2-digit",
	hour: "2-digit",
	minute: "2-digit",
	second: "2-digit",
	hour12: true,
})} PT`;

// Regex to find and replace the BUILD_TIME constant declaration
const regex = /const BUILD_TIME = ".*";/g;
const replacement = `const BUILD_TIME = "${formattedTime}";`;

if (content.match(regex)) {
	content = content.replace(regex, replacement);
	fs.writeFileSync(appTsxPath, content, "utf8");
	console.log(`[prebuild] Updated BUILD_TIME in App.tsx to: ${formattedTime}`);
} else {
	console.log("[prebuild] Could not find BUILD_TIME constant in App.tsx");
}
