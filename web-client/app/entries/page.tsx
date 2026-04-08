import { getEntries } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { EntriesManager } from "@/components/entries-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Entry as UIEntry } from "@/lib/swim-meet-types";

export const dynamic = "force-dynamic";

interface ServerEntry {
	id: number;
	eventId: number;
	athleteId: number;
	athleteName: string;
	teamId: number;
	teamName: string;
	teamColor?: string;
	seedTime: string;
	finalTime: string;
	place: number;
	eventName?: string;
	heat?: number;
	lane?: number;
	points?: number;
}

export default async function EntriesPage({
	searchParams,
}: {
	searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
	const params = await searchParams;
	const eventId = params.event as string | undefined;
	const athleteId = params.athlete as string | undefined;

	let mappedEntries: UIEntry[] = [];

	try {
		// Cast to unknown then to shape because proto definition is stale locally
		const list = (await getEntries(eventId, athleteId)) as unknown as {
			entries: ServerEntry[];
		};
		if (list?.entries) {
			mappedEntries = list.entries.map((e) => ({
				id: e.id.toString(), // assuming server provides index as ID
				eventName: e.eventName || `Event ${e.eventId}`, // Fallback if missing
				eventId: e.eventId.toString(),
				athleteId: e.athleteId.toString(),
				athleteName: e.athleteName,
				teamId: e.teamId ? e.teamId.toString() : "",
				teamName: e.teamName,
				teamColor: e.teamColor,
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
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<div className="flex-1 flex flex-col overflow-hidden">
					<div className="p-6 pb-0">
						<h1 className="text-2xl font-bold text-foreground">Entries</h1>
						<p className="text-muted-foreground">
							Manage individual event entries and results
						</p>
					</div>
					<EntriesManager initialEntries={mappedEntries} />
				</div>
			</SidebarInset>
		</>
	);
}
