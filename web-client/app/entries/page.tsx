"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { getEntries } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { EntriesManager } from "@/components/entries-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Entry as UIEntry } from "@/lib/swim-meet-types";

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

function EntriesPageContent() {
	const searchParams = useSearchParams();
	const eventId = searchParams.get("event") || undefined;
	const athleteId = searchParams.get("athlete") || undefined;

	const [mappedEntries, setMappedEntries] = useState<UIEntry[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		setLoading(true);
		getEntries(eventId, athleteId)
			.then((list: any) => {
				if (list?.entries) {
					const mapped = list.entries.map((e: ServerEntry) => ({
						id: e.id.toString(),
						eventName: e.eventName || `Event ${e.eventId}`,
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
					setMappedEntries(mapped);
				} else {
					setMappedEntries([]);
				}
			})
			.catch((e) => console.error("Failed to fetch entries", e))
			.finally(() => setLoading(false));
	}, [eventId, athleteId]);

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
					{loading ? (
						<div className="flex-1 flex items-center justify-center p-6">
							<span className="text-muted-foreground animate-pulse">
								Loading entries...
							</span>
						</div>
					) : (
						<EntriesManager initialEntries={mappedEntries} />
					)}
				</div>
			</SidebarInset>
		</>
	);
}

export default function EntriesPage() {
	return (
		<Suspense
			fallback={
				<div className="flex-1 flex items-center justify-center p-6">
					<span className="text-muted-foreground animate-pulse">
						Loading entries...
					</span>
				</div>
			}
		>
			<EntriesPageContent />
		</Suspense>
	);
}
