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
	outputFileTracingRoot: "../../",
	pageExtensions: isStatic ? ["tsx"] : ["js", "jsx", "ts", "tsx"],
	experimental: {
		serverActions: {
			bodySizeLimit: "50mb",
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
