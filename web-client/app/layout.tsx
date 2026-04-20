import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import NextTopLoader from "nextjs-toploader";
import type React from "react";
import "./globals.css";
import { AuthGuard } from "@/components/auth-guard";
import { ConfigProvider } from "@/components/config-provider";
import { SidebarProvider } from "@/components/ui/sidebar";
import { Providers } from "./providers";

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
	title: "MMTools - Swim Meet Data Management",
	description:
		"Interactive swim meet data management for meets, teams, athletes, events, and results",
	generator: "v0.app",
	icons: {
		icon: [
			{
				url: "/icon-light-32x32.png",
				media: "(prefers-color-scheme: light)",
			},
			{
				url: "/icon-dark-32x32.png",
				media: "(prefers-color-scheme: dark)",
			},
			{
				url: "/icon.svg",
				type: "image/xml+svg",
			},
		],
		apple: "/apple-icon.png",
	},
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en">
			<body className={`font-sans antialiased`}>
				<NextTopLoader
					color="var(--primary)"
					initialPosition={0.08}
					crawlSpeed={200}
					height={3}
					crawl={true}
					showSpinner={true}
					easing="ease"
					speed={200}
					shadow="0 0 10px var(--primary),0 0 5px var(--primary)"
				/>
				<Providers>
					<AuthGuard>
						<SidebarProvider defaultOpen={true}>
							<ConfigProvider>{children}</ConfigProvider>
						</SidebarProvider>
					</AuthGuard>
				</Providers>
			</body>
		</html>
	);
}
