"use client";

import { useEffect, useState } from "react";
import { getMeets } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { MeetsManager } from "@/components/meets-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

export default function MeetsPage() {
	const [mappedMeets, setMappedMeets] = useState<any[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		getMeets()
			.then((meetsResponse) => {
				if (meetsResponse?.meets) {
					setMappedMeets(meetsResponse.meets);
				}
			})
			.catch((e) => console.error("Failed to fetch meets", e))
			.finally(() => setLoading(false));
	}, []);

	return (
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<div className="flex-1 overflow-auto">
					<div className="p-6 pb-0">
						<h1 className="text-2xl font-bold text-foreground">Meets</h1>
						<p className="text-muted-foreground">
							Manage swimming meets and competitions
						</p>
						<div
							data-testid="meet-count"
							data-count={mappedMeets.length}
							className="hidden"
						/>
					</div>
					{loading ? (
						<div className="flex items-center justify-center p-6 min-h-[200px]">
							<span className="text-muted-foreground animate-pulse">
								Loading meets...
							</span>
						</div>
					) : (
						<MeetsManager initialMeets={mappedMeets} />
					)}
				</div>
			</SidebarInset>
		</>
	);
}
