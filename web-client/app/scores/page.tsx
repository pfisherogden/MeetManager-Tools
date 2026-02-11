import { getEventScores, getScores } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { ScoresManager } from "@/components/scores-manager";
import type { EventScore, Score as UIScore } from "@/lib/swim-meet-types";

export const dynamic = "force-dynamic";

interface ServerScore {
	meetName: string;
	teamId: number;
	teamName: string;
	individualPoints: number;
	relayPoints: number;
	totalPoints: number;
	rank: number;
}

interface ServerEventScoreEntry {
	id: number;
	athleteId: number;
	athleteName: string;
	teamId: number;
	teamName: string;
	seedTime: string;
	finalTime: string;
	place: number;
	points: number;
}

interface ServerEventScore {
	eventId: number;
	eventName: string;
	entries: ServerEventScoreEntry[];
}

export default async function ScoresPage() {
	let mappedScores: UIScore[] = [];

	let mappedEventScores: EventScore[] = [];

	try {
		const list = (await getScores()) as unknown as { scores: ServerScore[] };
		if (list?.scores) {
			mappedScores = list.scores.map((s, index) => ({
				id: `sc-${index}-${s.teamId}`,
				meetId: "1", // Placeholder
				meetName: s.meetName,
				teamId: s.teamId.toString(),
				teamName: s.teamName,
				individualPoints: s.individualPoints,
				relayPoints: s.relayPoints,
				totalPoints: s.totalPoints,
				rank: s.rank,
			}));
		}

		const evList = (await getEventScores()) as unknown as {
			eventScores: ServerEventScore[];
		};
		if (evList?.eventScores) {
			// Map entries inside
			mappedEventScores = evList.eventScores.map((ev) => ({
				eventId: ev.eventId.toString(),
				eventName: ev.eventName,
				entries: ev.entries.map((e) => ({
					id: e.id.toString(), // assuming server provides number
					eventId: ev.eventId.toString(),
					athleteId: e.athleteId.toString(), // assuming server provides number
					athleteName: e.athleteName,
					teamId: e.teamId.toString(), // assuming server provides number
					teamName: e.teamName,
					seedTime: e.seedTime,
					finalTime: e.finalTime,
					place: e.place || null,
					points: e.points || 0,
				})),
			}));
		}
	} catch (e) {
		console.error("Failed to fetch scores", e);
	}

	return (
		<div className="flex min-h-screen bg-background">
			<AppSidebar />
			<main className="flex-1 flex flex-col overflow-hidden">
				<div className="p-6 pb-0">
					<h1 className="text-2xl font-bold text-foreground">Scores</h1>
					<p className="text-muted-foreground">
						View and manage team scores and standings
					</p>
				</div>
				<ScoresManager
					initialScores={mappedScores}
					initialEventScores={mappedEventScores}
				/>
			</main>
		</div>
	);
}
