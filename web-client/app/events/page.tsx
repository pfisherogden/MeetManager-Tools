import { getEvents, getSessions } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { EventsManager } from "@/components/events-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Session, SwimEvent } from "@/lib/swim-meet-types";
import { formatAgeGroup } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function EventsPage() {
	let mappedEvents: SwimEvent[] = [];
	let sessions: Session[] = [];

	try {
		const [eventsList, sessionsList] = await Promise.all([
			getEvents(),
			getSessions(),
		]);

		if (eventsList?.events) {
			mappedEvents = eventsList.events.map((e) => ({
				id: e.id.toString(),
				sessionId: e.session.toString(),
				eventNumber: e.eventNo, // Use correct field
				distance: e.distance,
				stroke: e.stroke,
				gender: e.gender,
				ageGroup: e.ageGroup || formatAgeGroup(e.lowAge, e.highAge),
				entryCount: e.entryCount || 0,
				isRelay: e.isRelay,
			}));
		}

		if (sessionsList?.sessions) {
			sessions = sessionsList.sessions.map((s) => ({
				id: s.id,
				meetId: s.meetId,
				name: s.name,
				date: s.date,
				startTime: s.startTime,
				warmUpTime: s.warmUpTime,
				eventCount: s.eventCount,
			}));
		}
	} catch (e) {
		console.error("Failed to fetch events or sessions", e);
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
						<h1 className="text-2xl font-bold text-foreground">Events</h1>
						<p className="text-muted-foreground">
							Manage swim events and heats
						</p>
					</div>
					<EventsManager initialEvents={mappedEvents} sessions={sessions} />
				</div>
			</SidebarInset>
		</>
	);
}
