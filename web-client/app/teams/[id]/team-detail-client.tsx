"use client";

import { ArrowLeft, MapPin } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getTeam } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

export function TeamDetailClient({ id }: { id: string }) {
	const teamId = parseInt(id, 10);

	const [team, setTeam] = useState<any>(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		setLoading(true);
		getTeam(teamId)
			.then((response) => {
				if (response?.team) {
					setTeam(response.team);
				}
			})
			.catch((e) => console.error("Failed to load team", e))
			.finally(() => setLoading(false));
	}, [teamId]);

	if (loading) {
		return (
			<>
				<AppSidebar />
				<SidebarInset className="flex flex-col">
					<div className="p-4 border-b flex items-center gap-4">
						<SidebarTrigger />
						<div className="flex items-center gap-4">
							<span className="text-muted-foreground animate-pulse">
								Loading team details...
							</span>
						</div>
					</div>
				</SidebarInset>
			</>
		);
	}

	if (!team?.id) {
		return (
			<>
				<AppSidebar />
				<SidebarInset className="flex flex-col">
					<div className="p-4 border-b flex items-center gap-4">
						<SidebarTrigger />
						<Link
							href="/teams"
							className="text-muted-foreground hover:text-foreground flex items-center gap-1"
						>
							<ArrowLeft className="h-4 w-4" />
							Back to Teams
						</Link>
					</div>
					<div className="p-6 text-center text-muted-foreground">
						Team not found.
					</div>
				</SidebarInset>
			</>
		);
	}

	return (
		<>
			<AppSidebar />
			<SidebarInset className="flex flex-col">
				<div className="p-4 border-b flex items-center gap-4">
					<SidebarTrigger />
					<div className="flex items-center gap-4">
						<Link
							href="/teams"
							className="text-muted-foreground hover:text-foreground flex items-center gap-1"
						>
							<ArrowLeft className="h-4 w-4" />
							Back to Teams
						</Link>
					</div>
				</div>

				<div className="p-6 max-w-4xl w-full mx-auto space-y-6">
					<div>
						<h1 className="text-3xl font-bold">{team.name}</h1>
						<div className="flex items-center gap-2 mt-2 text-muted-foreground">
							<MapPin className="h-4 w-4" />
							<span>
								{team.city}, {team.state}
							</span>
						</div>
					</div>

					<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
						<div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm">
							<h2 className="text-lg font-semibold mb-4">Team Details</h2>
							<dl className="space-y-4">
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">
										Abbreviation
									</dt>
									<dd className="font-mono bg-muted px-2 py-0.5 rounded text-sm">
										{team.code}
									</dd>
								</div>
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">LSC</dt>
									<dd>{team.lsc || "-"}</dd>
								</div>
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">
										Athlete Count
									</dt>
									<dd>{team.athleteCount}</dd>
								</div>
							</dl>
						</div>
					</div>
				</div>
			</SidebarInset>
		</>
	);
}
