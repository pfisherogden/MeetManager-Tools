
import { AppSidebar } from "@/components/app-sidebar"
import { SessionsManager } from "@/components/sessions-manager"
import type { Session } from "@/lib/swim-meet-types"
import { getSessions } from "@/app/actions"

export const dynamic = 'force-dynamic';

export default async function SessionsPage() {
  let mappedSessions: Session[] = [];

  // Mock meets for now, eventually fetch from backend
  const meets = [{ id: "1", name: "Summer Championships" }];

  try {
    const response: any = await getSessions();
    if (response && response.sessions) {
      mappedSessions = response.sessions.map((s: any) => ({
        id: s.id,
        meetId: s.meetId,
        name: s.name,
        date: s.date,
        warmUpTime: s.warmUpTime,
        startTime: s.startTime,
        eventCount: s.eventCount,
      }));
    }
  } catch (e) {
    console.error("Failed to fetch sessions", e);
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-0">
          <h1 className="text-2xl font-bold text-foreground">Sessions</h1>
          <p className="text-muted-foreground">Manage meet sessions and schedules</p>
        </div>
        <SessionsManager initialSessions={mappedSessions} meets={meets} />
      </main>
    </div>
  )
}
