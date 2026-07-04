"use client";

import { useEffect, useState } from "react";
import { getEventScores, getScores } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { ScoresManager } from "@/components/scores-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Score as UIScore } from "@/lib/swim-meet-types";

export default function ScoresPage() {
	const [mappedScores, setMappedScores] = useState<UIScore[]>([]);
	const [mappedEventScores, setMappedEventScores] = useState<any[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		Promise.all([getScores(), getEventScores()])
			.then(([scoreList, eventScoresList]) => {
				if (scoreList?.scores) {
					const mapped = scoreList.scores.map((s) => ({
						id: s.teamId.toString(),
						meetId: "1",
						teamId: s.teamId.toString(),
						teamName: s.teamName,
						individualPoints: s.individualPoints,
						relayPoints: s.relayPoints,
						totalPoints: s.totalPoints,
						rank: s.rank,
						meetName: s.meetName,
					}));
					setMappedScores(mapped);
				}
				if (eventScoresList?.eventScores) {
					setMappedEventScores(eventScoresList.eventScores);
				}
			})
			.catch((e) => console.error("Failed to fetch scores", e))
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
						<h1 className="text-2xl font-bold text-foreground">Scores</h1>
						<p className="text-muted-foreground">
							Live meet scores and standings
						</p>
					</div>
					{loading ? (
						<div className="flex-1 flex items-center justify-center p-6">
							<span className="text-muted-foreground animate-pulse">
								Loading scores...
							</span>
						</div>
					) : (
						<ScoresManager
							initialScores={mappedScores}
							initialEventScores={mappedEventScores}
						/>
					)}
				</div>
			</SidebarInset>
		</>
	);
}
