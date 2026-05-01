import { getRelays } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { RelaysManager } from "@/components/relays-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Relay as UIRelay } from "@/lib/swim-meet-types";

export const dynamic = "force-dynamic";

export default async function RelaysPage({
	searchParams,
}: {
	searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
	const params = await searchParams;
	const eventId = params.event as string | undefined;

	let mappedRelays: UIRelay[] = [];

	try {
		const list = await getRelays(eventId);
		if (list?.relays) {
			mappedRelays = list.relays.map((r) => ({
				id: r.id.toString(),
				eventId: r.eventId.toString(),
				eventName: r.eventName || `Event ${r.eventId}`,
				teamId: r.teamId.toString(),
				teamName: r.teamName,
				teamColor: "", // Backend will provide if needed, or derived from teamId
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
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<div className="flex-1 flex flex-col overflow-hidden">
					<div className="p-6 pb-0">
						<h1 className="text-2xl font-bold text-foreground">Relays</h1>
						<p className="text-muted-foreground">
							Manage relay teams and entries
						</p>
					</div>
					<RelaysManager initialRelays={mappedRelays} />
				</div>
			</SidebarInset>
		</>
	);
}
