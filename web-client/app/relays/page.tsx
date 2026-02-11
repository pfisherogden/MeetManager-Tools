import { getRelays } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { RelaysManager } from "@/components/relays-manager";
import type { Relay as UIRelay } from "@/lib/swim-meet-types";

export const dynamic = "force-dynamic";

interface ServerRelay {
	id: number;
	eventId: number;
	eventName?: string;
	teamId: number;
	teamName: string;
	leg1Name: string;
	leg2Name: string;
	leg3Name: string;
	leg4Name: string;
	seedTime: string;
	finalTime?: string;
	place?: number;
}

export default async function RelaysPage() {
	let mappedRelays: UIRelay[] = [];

	try {
		const list = (await getRelays()) as unknown as { relays: ServerRelay[] };
		if (list?.relays) {
			mappedRelays = list.relays.map((r) => ({
				id: r.id.toString(),
				eventId: r.eventId.toString(),
				eventName: r.eventName || `Event ${r.eventId}`,
				teamId: r.teamId.toString(),
				teamName: r.teamName,
				leg1: r.leg1Name,
				leg2: r.leg2Name,
				leg3: r.leg3Name,
				leg4: r.leg4Name,
				seedTime: r.seedTime,
				finalTime: r.finalTime || null,
				place: r.place ? r.place : null,
			}));
		}
	} catch (e) {
		console.error("Failed to fetch relays", e);
	}

	return (
		<div className="flex min-h-screen bg-background">
			<AppSidebar />
			<main className="flex-1 flex flex-col overflow-hidden">
				<div className="p-6 pb-0">
					<h1 className="text-2xl font-bold text-foreground">Relays</h1>
					<p className="text-muted-foreground">
						Manage relay team entries and results
					</p>
				</div>
				<RelaysManager initialRelays={mappedRelays} />
			</main>
		</div>
	);
}
