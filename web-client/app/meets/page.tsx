import { AppSidebar } from "@/components/app-sidebar"
import { MeetsManager } from "@/components/meets-manager"
import type { Meet as UIMeet } from "@/lib/swim-meet-types"
import client from "@/lib/mm-client";
import { Empty, MeetList } from "@/lib/proto/meet_manager";

export const dynamic = 'force-dynamic';

// Helper to wrap callback in promise
function getMeets(): Promise<MeetList> {
  return new Promise((resolve, reject) => {
    client.getMeets(Empty.fromPartial({}), (err, response) => {
      if (err) {
        reject(err);
      } else {
        resolve(response);
      }
    });
  });
}



export default async function MeetsPage() {
  let mappedMeets: UIMeet[] = [];

  try {
    const list = await getMeets();
    mappedMeets = list.meets.map(m => ({
      id: m.id,
      name: m.name,
      location: m.location,
      startDate: m.startDate,
      endDate: m.endDate,
      poolType: "SCY", // Default or parsed from location?
      status: (m.status as "upcoming" | "active" | "completed") || "upcoming"
    }));
  } catch (e) {
    console.error("Failed to fetch meets", e);
  }

  // Need a client component wrapper for DataTablestate? 
  // For now, I'll pass data to a Client Component manager similar to other pages.
  // But wait, the previous page was a Client Component itself ("use client").
  // So I need to refactor this page to be a Server Component that passes data to a Client Component.
  // OR I can fetch in useEffect (Client Side Fetching). 
  // Given the "use client" directive at top, I should probably stick to Client Fetching OR refactor to Server Component pattern like I did for Teams/Athletes.

  // Refactoring to Server Component pattern (TeamsPage style) is cleaner for Next.js 13+
  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-0">
          <h1 className="text-2xl font-bold text-foreground">Swim Meets</h1>
          <p className="text-muted-foreground">Manage your swim meet schedule and details</p>
        </div>
        <MeetsManager initialMeets={mappedMeets} />
      </main>
    </div>
  )
}
