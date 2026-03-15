import { getDashboardStats } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { Dashboard } from "@/components/dashboard";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { DashboardStats } from "@/lib/proto/meetmanager/v1/meet_manager";

export const dynamic = "force-dynamic";

export default async function HomePage() {
	let stats: DashboardStats = {
		meetCount: 0,
		teamCount: 0,
		athleteCount: 0,
		eventCount: 0,
	};

	try {
		const fetchedStats = await getDashboardStats();
		if (fetchedStats) {
			stats = fetchedStats;
		}
	} catch (e) {
		console.error("Failed to fetch dashboard stats", e);
	}

	return (
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<main className="flex-1 overflow-auto">
					<Dashboard stats={stats} />
				</main>
			</SidebarInset>
		</>
	);
}
