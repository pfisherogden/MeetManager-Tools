"use client";

import { Inter } from "next/font/google";
import NextTopLoader from "nextjs-toploader";
import { useEffect, useState } from "react";
import "./globals.css";
import { ConfigProvider } from "@/components/config-provider";
import { SidebarProvider } from "@/components/ui/sidebar";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	const [hydrated, setHydrated] = useState(false);
	useEffect(() => {
		setHydrated(true);
	}, []);

	return (
		<html lang="en">
			<body
				className={`${inter.variable} font-sans antialiased`}
				data-hydrated={hydrated}
			>
				<NextTopLoader
					color="var(--primary)"
					initialPosition={0.08}
					crawlSpeed={200}
					height={3}
					crawl={true}
					showSpinner={true}
					easing="ease"
					speed={200}
					shadow="0 0 10px var(--primary), 0 0 5px var(--primary)"
				/>
				<Providers>
					<SidebarProvider defaultOpen={true}>
						<ConfigProvider>{children}</ConfigProvider>
					</SidebarProvider>
				</Providers>
			</body>
		</html>
	);
}
