import type { Score as UIScore } from "@/lib/swim-meet-types"
import { ScoresManager } from "@/components/scores-manager"
import { AppSidebar } from "@/components/app-sidebar"

import { getScores } from "@/app/actions"

export const dynamic = 'force-dynamic';

export default async function ScoresPage() {
  let mappedScores: UIScore[] = [];

  try {
    const list: any = await getScores();
    if (list && list.scores) {
      mappedScores = list.scores.map((s: any, index: number) => ({
        id: `sc-${index}-${s.teamId}`,
        meetId: "1", // Placeholder, as scores are usually per meet
        teamId: s.teamId.toString(),
        teamName: s.teamName,
        individualPoints: s.individualPoints,
        relayPoints: s.relayPoints,
        totalPoints: s.totalPoints,
        rank: s.rank
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
        <ScoresManager initialScores={mappedScores} />
      </main>
    </div>
  )
}
