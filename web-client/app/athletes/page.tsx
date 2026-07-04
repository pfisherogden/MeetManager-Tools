"use client";

import { useEffect, useState } from "react";
import { getAthletes, getTeams } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { AthletesManager } from "@/components/athletes-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Athlete as UIAthlete } from "@/lib/swim-meet-types";

export default function AthletesPage() {
	const [mappedAthletes, setMappedAthletes] = useState<UIAthlete[]>([]);
	const [teamOptions, setTeamOptions] = useState<
		{ id: string; name: string }[]
	>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		Promise.all([getAthletes(), getTeams()])
			.then(([athleteList, teamsResponse]) => {
				const teamColorMap: Record<number, string> = {};
				if (teamsResponse?.teams) {
					const options = teamsResponse.teams.map((t) => ({
						id: t.id.toString(),
						name: t.name,
					}));
					setTeamOptions(options);
					for (const t of teamsResponse.teams) {
						teamColorMap[t.id] = t.color;
					}
				}

				if (athleteList?.athletes) {
					const athletes = athleteList.athletes.map((a) => ({
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
					setMappedAthletes(athletes);
				}
			})
			.catch((e) => console.error("Failed to fetch athletes or teams", e))
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
						<h1 className="text-2xl font-bold text-foreground">Athletes</h1>
						<p className="text-muted-foreground">
							Manage athlete profiles and team assignments
						</p>
					</div>
					{loading ? (
						<div className="flex items-center justify-center p-6 min-h-[200px]">
							<span className="text-muted-foreground animate-pulse">
								Loading athletes...
							</span>
						</div>
					) : (
						<AthletesManager
							initialAthletes={mappedAthletes}
							teams={teamOptions}
						/>
					)}
				</div>
			</SidebarInset>
		</>
	);
}
