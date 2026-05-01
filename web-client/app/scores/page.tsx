import { getEventScores, getScores } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { ScoresManager } from "@/components/scores-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Score as UIScore } from "@/lib/swim-meet-types";

export const dynamic = "force-dynamic";

export default async function ScoresPage() {
	let mappedScores: UIScore[] = [];
	let mappedEventScores: any[] = [];

	try {
		const [scoreList, eventScoresList] = await Promise.all([
			getScores(),
			getEventScores(),
		]);

		if (scoreList?.scores) {
			mappedScores = scoreList.scores.map((s) => ({
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
		}

		if (eventScoresList?.eventScores) {
			mappedEventScores = eventScoresList.eventScores;
		}
	} catch (e) {
		console.error("Failed to fetch scores", e);
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
						<h1 className="text-2xl font-bold text-foreground">Scores</h1>
						<p className="text-muted-foreground">
							Live meet scores and standings
						</p>
					</div>
					<ScoresManager
						initialScores={mappedScores}
						initialEventScores={mappedEventScores}
					/>
				</div>
			</SidebarInset>
		</>
	);
}
