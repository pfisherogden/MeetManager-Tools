"use client";

import { useEffect, useState } from "react";
import { getDashboardStats } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { Dashboard } from "@/components/dashboard";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

export default function HomePage() {
	const [stats, setStats] = useState<any>({
		meetCount: 0,
		teamCount: 0,
		athleteCount: 0,
		eventCount: 0,
		totalAthletes: 0,
		totalTeams: 0,
		totalEvents: 0,
		totalResults: 0,
	});
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const startTime = performance.now();
		console.log("[Performance] Dashboard load sequence initiated.");
		getDashboardStats()
			.then((fetchedStats) => {
				if (fetchedStats) {
					setStats(fetchedStats);
				}
				const duration = performance.now() - startTime;
				console.log(
					`[Performance] Dashboard stats loaded in ${duration.toFixed(1)}ms`,
				);
			})
			.catch((e) => {
				console.error("[Performance] Failed to fetch dashboard stats", e);
			})
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
					{loading ? (
						<div className="flex h-full w-full items-center justify-center p-6 min-h-[200px]">
							<span className="text-muted-foreground animate-pulse">
								Loading dashboard...
							</span>
						</div>
					) : (
						<Dashboard stats={stats} />
					)}
				</div>
			</SidebarInset>
		</>
	);
}
