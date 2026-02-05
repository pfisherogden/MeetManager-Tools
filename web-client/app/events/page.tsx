import type { SwimEvent as UIEvent } from "@/lib/swim-meet-types"
import { EventsManager } from "@/components/events-manager"
import { AppSidebar } from "@/components/app-sidebar"

import { getEvents } from "@/app/actions"

function formatAgeGroup(low: number, high: number): string {
  if (low === 0 && high === 0) return "Open";
  if (low === 0 && high > 0) return `${high}&U`;
  if (low > 0 && high === 0) return `${low}&O`; // Or 100+?
  if (high === 99 || high > 99) return `${low}&O`;
  return `${low}-${high}`;
}

export const dynamic = 'force-dynamic';

export default async function EventsPage() {
  let mappedEvents: UIEvent[] = [];

  try {
    const list: any = await getEvents();
    if (list && list.events) {
      mappedEvents = list.events.map((e: any) => ({
        id: e.id.toString(),
        sessionId: e.session.toString(), // Needs robust mapping if sessions are entities
        eventNumber: e.id, // Assuming ID is event number
        distance: e.distance,
        stroke: e.stroke,
        gender: e.gender,
        ageGroup: formatAgeGroup(e.lowAge, e.highAge),
        entryCount: 0 // Not yet provided by API
      }));
    }
  } catch (e) {
    console.error("Failed to fetch events", e);
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-0">
          <h1 className="text-2xl font-bold text-foreground">Events</h1>
          <p className="text-muted-foreground">Manage swim events and heats</p>
        </div>
        <EventsManager initialEvents={mappedEvents} />
      </main>
    </div>
  )
}
