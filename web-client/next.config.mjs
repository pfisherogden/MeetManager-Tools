const isStatic = process.env.EXPORT_STATIC === "true";

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
	experimental: isStatic
		? {}
		: {
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
				turbopack: {
					resolveAlias: {
						"@/app/actions": "./app/actions.client.ts",
					},
				},
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
