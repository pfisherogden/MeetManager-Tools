import type { Relay as UIRelay } from "@/lib/swim-meet-types"
import client from "@/lib/mm-client";
import { Empty } from "@/lib/proto/meet_manager";
import { RelaysManager } from "@/components/relays-manager"
import { AppSidebar } from "@/components/app-sidebar"

// Helper to wrap callback in promise
function getRelays(): Promise<any> {
  return new Promise((resolve, reject) => {
    // @ts-ignore
    client.getRelays(Empty.fromPartial({}), (err: any, response: any) => {
      if (err) {
        reject(err);
      } else {
        resolve(response);
      }
    });
  });
}

export const dynamic = 'force-dynamic';

export default async function RelaysPage() {
  let mappedRelays: UIRelay[] = [];

  try {
    const list = await getRelays();
    mappedRelays = list.relays.map((r: any) => ({
      id: r.id.toString(),
      eventId: r.eventId.toString(), // Map if needed
      teamId: r.teamId.toString(),
      teamName: r.teamName,
      leg1: r.leg1Name,
      leg2: r.leg2Name,
      leg3: r.leg3Name,
      leg4: r.leg4Name,
      seedTime: r.seedTime,
      finalTime: r.finalTime || null,
      place: r.place || null,
    }));
  } catch (e) {
    console.error("Failed to fetch relays", e);
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-0">
          <h1 className="text-2xl font-bold text-foreground">Relays</h1>
          <p className="text-muted-foreground">Manage relay team entries and results</p>
        </div>
        <RelaysManager initialRelays={mappedRelays} />
      </main>
    </div>
  )
}
