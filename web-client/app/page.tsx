import { AppSidebar } from "@/components/app-sidebar"
import { Dashboard } from "@/components/dashboard"
import client from "@/lib/mm-client";
import { Empty, DashboardStats } from "@/lib/proto/meet_manager";
export const dynamic = 'force-dynamic';

// Helper to wrap callback in promise
function getStats(): Promise<DashboardStats> {
  return new Promise((resolve, reject) => {
    client.getDashboardStats(Empty.fromPartial({}), (err, response) => {
      if (err) {
        reject(err);
      } else {
        resolve(response);
      }
    });
  });
}

export default async function HomePage() {
  let stats: DashboardStats = {
    meetCount: 0,
    teamCount: 0,
    athleteCount: 0,
    eventCount: 0
  };

  try {
    stats = await getStats();
  } catch (e) {
    console.error("Failed to fetch dashboard stats", e);
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <main className="flex-1 overflow-auto">
        <Dashboard stats={stats} />
      </main>
    </div>
  )
}
