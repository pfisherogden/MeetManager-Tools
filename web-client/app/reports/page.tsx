import { getTeams } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { ReportsManager } from "@/components/reports-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Team as UITeam } from "@/lib/swim-meet-types";

export const dynamic = "force-dynamic";

interface ServerTeam {
	id: number;
	name: string;
	code: string;
}

export default async function ReportsPage() {
	let mappedTeams: UITeam[] = [];

	try {
		const list = (await getTeams()) as unknown as { teams: ServerTeam[] };
		if (list?.teams) {
			mappedTeams = list.teams.map((t) => ({
				id: t.id.toString(),
				name: t.name,
				code: t.code,
				athleteCount: 0,
			}));
		}
	} catch (e) {
		console.error("Failed to fetch teams for reports", e);
	}

	return (
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<div className="flex-1 flex flex-col overflow-hidden">
					<div className="p-6 pb-0">
						<h1 className="text-2xl font-bold">Reports</h1>
						<p className="text-muted-foreground">
							Generate and customize PDF reports from meet data
						</p>
					</div>
					<ReportsManager initialTeams={mappedTeams} />
				</div>
			</SidebarInset>
		</>
	);
}
