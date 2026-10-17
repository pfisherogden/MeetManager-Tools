import path from "node:path";
import { fileURLToPath } from "node:url";

const isStatic = process.env.EXPORT_STATIC === "true";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** @type {import('next').NextConfig} */
const nextConfig = {
	typescript: {
		ignoreBuildErrors: true,
	},
	images: {
		unoptimized: true,
	},
	trailingSlash: true,
	outputFileTracingRoot: "../../",
	pageExtensions: isStatic ? ["tsx"] : ["js", "jsx", "ts", "tsx"],
	experimental: {
		serverActions: {
			bodySizeLimit: "50mb",
			allowedOrigins: [
				"mmtools-app.web.app",
				"mmtools-app.firebaseapp.com",
				"mmtools-488404.web.app",
				"mmtools-488404.firebaseapp.com",
				"*.web.app",
				"*.firebaseapp.com",
				"*.run.app",
				"localhost:3000",
				"127.0.0.1:3000",
			],
		},
	},
	generateBuildId: async () => {
		return `build-${Date.now()}`;
	},
	env: {
		NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
	},
	...(isStatic
		? {
				output: "export",
			}
		: {
				async rewrites() {
					return [
						{
							source: "/judge/:path*",
							destination: "/judge/index.html",
						},
					];
				},
			}),
};

export default nextConfig;
