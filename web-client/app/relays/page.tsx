"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { getRelays } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { RelaysManager } from "@/components/relays-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Relay as UIRelay } from "@/lib/swim-meet-types";

function RelaysPageContent() {
	const searchParams = useSearchParams();
	const eventId = searchParams.get("event") || undefined;

	const [mappedRelays, setMappedRelays] = useState<UIRelay[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		setLoading(true);
		getRelays(eventId)
			.then((list) => {
				if (list?.relays) {
					const mapped = list.relays.map((r) => ({
						id: String(r.id),
						eventId: String(r.eventId),
						eventName: r.eventName || `Event ${r.eventId}`,
						teamId: String(r.teamId),
						teamName: r.teamName,
						teamColor: "",
						leg1: r.leg1Name,
						leg2: r.leg2Name,
						leg3: r.leg3Name,
						leg4: r.leg4Name,
						seedTime: r.seedTime,
						finalTime: r.finalTime || null,
						place: r.place ? r.place : null,
					}));
					setMappedRelays(mapped);
				} else {
					setMappedRelays([]);
				}
			})
			.catch((e) => console.error("Failed to fetch relays", e))
			.finally(() => setLoading(false));
	}, [eventId]);

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
					{loading ? (
						<div className="flex-1 flex items-center justify-center p-6">
							<span className="text-muted-foreground animate-pulse">
								Loading relays...
							</span>
						</div>
					) : (
						<RelaysManager initialRelays={mappedRelays} />
					)}
				</div>
			</SidebarInset>
		</>
	);
}

export default function RelaysPage() {
	return (
		<Suspense
			fallback={
				<div className="flex-1 flex items-center justify-center p-6">
					<span className="text-muted-foreground animate-pulse">
						Loading relays...
					</span>
				</div>
			}
		>
			<RelaysPageContent />
		</Suspense>
	);
}
