"use client";

import { useEffect, useState } from "react";
import { getTeams } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { ReportsManager } from "@/components/reports-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Team as UITeam } from "@/lib/swim-meet-types";

interface ServerTeam {
	id: number;
	name: string;
	code: string;
}

export default function ReportsPage() {
	const [mappedTeams, setMappedTeams] = useState<UITeam[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		getTeams()
			.then((list: any) => {
				if (list?.teams) {
					const mapped = list.teams.map((t: ServerTeam) => ({
						id: String(t.id),
						name: t.name,
						abbreviation: t.code || "",
						city: "",
						state: "",
						athleteCount: 0,
						color: "#000000",
					}));
					setMappedTeams(mapped);
				}
			})
			.catch((e) => console.error("Failed to fetch teams for reports", e))
			.finally(() => setLoading(false));
	}, []);

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
					{loading ? (
						<div className="flex-1 flex items-center justify-center p-6">
							<span className="text-muted-foreground animate-pulse">
								Loading reports...
							</span>
						</div>
					) : (
						<ReportsManager initialTeams={mappedTeams} />
					)}
				</div>
			</SidebarInset>
		</>
	);
}
