/** @type {import('next').NextConfig} */
const nextConfig = {
	typescript: {
		ignoreBuildErrors: true,
	},
	images: {
		unoptimized: true,
	},
	experimental: {
		serverActions: {
			bodySizeLimit: "50mb",
		},
		outputFileTracingRoot: "../../",
	},
	env: {
		NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
	},
	async rewrites() {
		return [
			{
				source: "/judge/:path*",
				destination: "/judge/index.html",
			},
		];
	},
};

export default nextConfig;
