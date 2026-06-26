const { execSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

// 1. Create target folder
fs.mkdirSync("./lib/proto", { recursive: true });

// 2. Detect OS to resolve plugin path
const isWindows = process.platform === "win32";
const pluginExt = isWindows ? ".cmd" : "";
const pluginPath = path.join(
	"node_modules",
	".bin",
	`protoc-gen-ts_proto${pluginExt}`,
);

// 3. Construct and run command
const cmd = `grpc_tools_node_protoc --plugin=protoc-gen-ts_proto=${pluginPath} --ts_proto_out=./lib/proto --ts_proto_opt=outputServices=nice-grpc,outputServices=generic-definitions,esModuleInterop=true,forceLong=string,unrecognizedEnum=false,outputPartialMethods=false -I ../protos ../protos/meetmanager/v1/meet_manager.proto`;

console.log(`Running: ${cmd}`);
try {
	execSync(cmd, { stdio: "inherit" });
	console.log("Protos generated successfully.");
} catch (error) {
	console.error("Failed to generate protos:", error);
	process.exit(1);
}
