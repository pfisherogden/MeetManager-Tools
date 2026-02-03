import { AppSidebar } from "@/components/app-sidebar"
import { TeamsManager } from "@/components/teams-manager"
import type { Team as UITeam } from "@/lib/swim-meet-types"
import client from "@/lib/mm-client";
import { Empty, TeamList } from "@/lib/proto/meet_manager";

export const dynamic = 'force-dynamic';

// Helper to wrap callback in promise
function getTeams(): Promise<TeamList> {
  return new Promise((resolve, reject) => {
    client.getTeams(Empty.fromPartial({}), (err, response) => {
      if (err) {
        reject(err);
      } else {
        resolve(response);
      }
    });
  });
}



export default async function TeamsPage() {
  let mappedTeams: UITeam[] = [];

  try {
    const teamList = await getTeams();
    mappedTeams = teamList.teams.map(t => ({
      id: t.id.toString(),
      name: t.name,
      abbreviation: t.code,
      city: t.city,
      state: t.state,
      athleteCount: t.athleteCount,
      color: "#0077B6" // Default color
    }));
  } catch (e) {
    console.error("Failed to fetch teams", e);
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-0">
          <h1 className="text-2xl font-bold text-foreground">Teams</h1>
          <p className="text-muted-foreground">Manage participating swim teams</p>
        </div>
        <TeamsManager initialTeams={mappedTeams} />
      </main>
    </div>
  )
}
