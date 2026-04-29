/** @type {import('next').NextConfig} */
const nextConfig = {
	typescript: {
		ignoreBuildErrors: true,
	},
	images: {
		unoptimized: true,
	},
	outputFileTracingRoot: "../../",
	experimental: {
		serverActions: {
			bodySizeLimit: "50mb",
		},
	},
	generateBuildId: async () => {
		return `build-${new Date().getTime()}`;
	},
	env: {
		NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
	},
	async rewrites() {
		return [];
	},
};

export default nextConfig;
