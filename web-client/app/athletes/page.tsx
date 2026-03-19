import { getAthletes, getTeams } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { AthletesManager } from "@/components/athletes-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Athlete as UIAthlete } from "@/lib/swim-meet-types";

export const dynamic = "force-dynamic";

interface ServerAthlete {
	id: number;
	firstName: string;
	lastName: string;
	teamId: number;
	teamName: string;
	gender: string;
	age: number;
	dateOfBirth: string;
}

interface ServerTeam {
	id: number;
	name: string;
	color: string;
}

export default async function AthletesPage() {
	let mappedAthletes: (UIAthlete & { teamColor?: string })[] = [];
	let teamOptions: string[] = [];

	try {
		const [athleteList, teamList] = await Promise.all([
			getAthletes() as unknown as { athletes: ServerAthlete[] },
			getTeams() as unknown as { teams: ServerTeam[] },
		]);

		const teamColorMap: Record<number, string> = {};
		if (teamList?.teams) {
			teamOptions = teamList.teams.map((t) => t.name).sort();
			for (const t of teamList.teams) {
				teamColorMap[t.id] = t.color;
			}
		}

		if (athleteList?.athletes) {
			mappedAthletes = athleteList.athletes.map((a) => ({
				id: a.id.toString(),
				firstName: a.firstName,
				lastName: a.lastName,
				teamId: a.teamId.toString(),
				teamName: a.teamName,
				dateOfBirth: a.dateOfBirth,
				gender: a.gender as "M" | "F",
				age: a.age,
				teamColor: teamColorMap[a.teamId],
			}));
		}
	} catch (e) {
		console.error("Failed to fetch athletes", e);
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
						<h1 className="text-2xl font-bold text-foreground">Athletes</h1>
						<p className="text-muted-foreground">
							Manage athlete profiles and team assignments
						</p>
					</div>
					<AthletesManager
						initialAthletes={mappedAthletes}
						teams={teamOptions}
					/>
				</div>
			</SidebarInset>
		</>
	);
}
