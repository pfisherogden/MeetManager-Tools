import { getEvents } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { EventsManager } from "@/components/events-manager";
import type { SwimEvent } from "@/lib/swim-meet-types";
import { formatAgeGroup } from "@/lib/utils";

export const dynamic = "force-dynamic";

interface ServerEvent {
	id: number;
	session: number;
	distance: number;
	stroke: string;
	gender: string;
	lowAge: number;
	highAge: number;
	entryCount: number;
	ageGroup?: string;
}

export default async function EventsPage() {
	let mappedEvents: SwimEvent[] = [];

	try {
		const list = (await getEvents()) as unknown as { events: ServerEvent[] };
		if (list?.events) {
			mappedEvents = list.events.map((e) => ({
				id: e.id.toString(),
				sessionId: e.session.toString(), // Needs robust mapping if sessions are entities
				eventNumber: e.id, // Assuming ID is event number
				distance: e.distance,
				stroke: e.stroke,
				gender: e.gender,
				ageGroup: e.ageGroup || formatAgeGroup(e.lowAge, e.highAge),
				entryCount: e.entryCount || 0,
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
	);
}
