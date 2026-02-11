import { getEntries } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { EntriesManager } from "@/components/entries-manager";
import type { Entry as UIEntry } from "@/lib/swim-meet-types";

export const dynamic = "force-dynamic";

interface ServerEntry {
	id: number;
	eventId: number;
	athleteId: number;
	athleteName: string;
	teamId: number;
	teamName: string;
	seedTime: string;
	finalTime: string;
	place: number;
	eventName?: string;
	heat?: number;
	lane?: number;
	points?: number;
}

export default async function EntriesPage() {
	let mappedEntries: UIEntry[] = [];

	try {
		// Cast to unknown then to shape because proto definition is stale locally
		const list = (await getEntries()) as unknown as { entries: ServerEntry[] };
		if (list?.entries) {
			mappedEntries = list.entries.map((e) => ({
				id: e.id.toString(), // assuming server provides index as ID
				eventName: e.eventName || `Event ${e.eventId}`, // Fallback if missing
				eventId: e.eventId.toString(),
				athleteId: e.athleteId.toString(),
				athleteName: e.athleteName,
				teamId: e.teamId ? e.teamId.toString() : "",
				teamName: e.teamName,
				seedTime: e.seedTime,
				finalTime: e.finalTime || null,
				place: e.place || null,
				heat: e.heat || 0,
				lane: e.lane || 0,
				points: e.points || 0,
			}));
		}
	} catch (e) {
		console.error("Failed to fetch entries", e);
	}

	return (
		<div className="flex min-h-screen bg-background">
			<AppSidebar />
			<main className="flex-1 flex flex-col overflow-hidden">
				<div className="p-6 pb-0">
					<h1 className="text-2xl font-bold text-foreground">Entries</h1>
					<p className="text-muted-foreground">
						Manage individual event entries and results
					</p>
				</div>
				<EntriesManager initialEntries={mappedEntries} />
			</main>
		</div>
	);
}
