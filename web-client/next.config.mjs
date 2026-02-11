/** @type {import('next').NextConfig} */
const nextConfig = {
	typescript: {
		ignoreBuildErrors: true,
	},
	images: {
		unoptimized: true,
	},
	output: "standalone",
	experimental: {
		serverActions: {
			bodySizeLimit: "50mb",
		},
	},
	env: {
		NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
	},
};

export default nextConfig;
