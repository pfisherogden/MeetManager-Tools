import { getDashboardStats } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { Dashboard } from "@/components/dashboard";
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
		<div className="flex min-h-screen bg-background">
			<AppSidebar />
			<main className="flex-1 overflow-auto">
				<Dashboard stats={stats} />
			</main>
		</div>
	);
}
