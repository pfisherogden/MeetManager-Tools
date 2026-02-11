import { getAthletes, getTeams } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { AthletesManager } from "@/components/athletes-manager";
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
}

export default async function AthletesPage() {
	let mappedAthletes: UIAthlete[] = [];
	let teamOptions: string[] = [];

	try {
		const [athleteList, teamList] = await Promise.all([
			getAthletes() as unknown as { athletes: ServerAthlete[] },
			getTeams() as unknown as { teams: { name: string }[] },
		]);

		if (teamList?.teams) {
			teamOptions = teamList.teams.map((t) => t.name).sort();
		}

		if (athleteList?.athletes) {
			mappedAthletes = athleteList.athletes.map((a) => ({
				id: a.id.toString(),
				firstName: a.firstName,
				lastName: a.lastName,
				teamId: a.teamId.toString(),
				teamName: a.teamName,
				dateOfBirth: "2010-01-01", // Placeholder as DoB is not in current proto
				gender: a.gender as "M" | "F",
				age: a.age,
			}));
		}
	} catch (e) {
		console.error("Failed to fetch athletes", e);
	}

	return (
		<div className="flex min-h-screen bg-background">
			<AppSidebar />
			<main className="flex-1 flex flex-col overflow-hidden">
				<div className="p-6 pb-0">
					<h1 className="text-2xl font-bold text-foreground">Athletes</h1>
					<p className="text-muted-foreground">
						Manage athlete profiles and team assignments
					</p>
				</div>
				<AthletesManager initialAthletes={mappedAthletes} teams={teamOptions} />
			</main>
		</div>
	);
}
