import type { Entry as UIEntry } from "@/lib/swim-meet-types"
import client from "@/lib/mm-client";
import { Empty } from "@/lib/proto/meet_manager";
import { EntriesManager } from "@/components/entries-manager"
import { AppSidebar } from "@/components/app-sidebar"

// Helper to wrap callback in promise
function getEntries(): Promise<any> {
  return new Promise((resolve, reject) => {
    // @ts-ignore
    client.getEntries(Empty.fromPartial({}), (err: any, response: any) => {
      if (err) {
        reject(err);
      } else {
        resolve(response);
      }
    });
  });
}

export default async function EntriesPage() {
  let mappedEntries: UIEntry[] = [];

  try {
    const list = await getEntries();
    mappedEntries = list.entries.map((e: any) => ({
      id: e.id.toString(), // assuming server provides index as ID
      eventId: e.eventId.toString(),
      athleteId: e.athleteId.toString(),
      athleteName: e.athleteName,
      teamName: e.teamName,
      seedTime: e.seedTime,
      finalTime: e.finalTime || null,
      place: e.place || null,
    }));
  } catch (e) {
    console.error("Failed to fetch entries", e);
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-0">
          <h1 className="text-2xl font-bold text-foreground">Entries</h1>
          <p className="text-muted-foreground">Manage individual event entries and results</p>
        </div>
        <EntriesManager initialEntries={mappedEntries} />
      </main>
    </div>
  )
}
