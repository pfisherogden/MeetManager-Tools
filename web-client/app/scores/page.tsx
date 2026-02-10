import type { Score as UIScore } from "@/lib/swim-meet-types"
import { ScoresManager } from "@/components/scores-manager"
import { AppSidebar } from "@/components/app-sidebar"

import { getScores, getEventScores } from "@/app/actions"
import type { EventScore } from "@/lib/swim-meet-types"

export const dynamic = 'force-dynamic';

export default async function ScoresPage() {
  let mappedScores: UIScore[] = [];

  let mappedEventScores: EventScore[] = [];

  try {
    const list: any = await getScores();
    if (list && list.scores) {
      mappedScores = list.scores.map((s: any, index: number) => ({
        id: `sc-${index}-${s.teamId}`,
        meetId: "1", // Placeholder
        meetName: s.meetName,
        teamId: s.teamId.toString(),
        teamName: s.teamName,
        individualPoints: s.individualPoints,
        relayPoints: s.relayPoints,
        totalPoints: s.totalPoints,
        rank: s.rank
      }));
    }

    const evList: any = await getEventScores();
    if (evList && evList.eventScores) {
      // Map entries inside
      mappedEventScores = evList.eventScores.map((ev: any) => ({
        eventId: ev.eventId.toString(),
        eventName: ev.eventName,
        entries: ev.entries.map((e: any) => ({
          id: e.id,
          eventId: ev.eventId.toString(),
          athleteId: e.athleteId,
          athleteName: e.athleteName,
          teamId: e.teamId,
          teamName: e.teamName,
          seedTime: e.seedTime,
          finalTime: e.finalTime,
          place: e.place || null,
          points: e.points || 0
        }))
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
          <p className="text-muted-foreground">View and manage team scores and standings</p>
        </div>
        <ScoresManager initialScores={mappedScores} initialEventScores={mappedEventScores} />
      </main>
    </div>
  )
}
