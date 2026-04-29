"use client";

import NextTopLoader from "nextjs-toploader";
import { useEffect, useState } from "react";
import { ConfigProvider } from "@/components/config-provider";
import { SidebarProvider } from "@/components/ui/sidebar";
import { Providers } from "./providers";

export function ClientLayout({ children }: { children: React.ReactNode }) {
	const [_hydrated, setHydrated] = useState(false);
	useEffect(() => {
		setHydrated(true);
		// Force the attribute on the body since we wrap everything
		document.body.setAttribute("data-hydrated", "true");
	}, []);

	return (
		<>
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
		</>
	);
}
