"use client";

import { useEffect, useState } from "react";
import { getSessions } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { SessionsManager } from "@/components/sessions-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import type { Session } from "@/lib/swim-meet-types";

interface ServerSession {
	id: string;
	meetId: string;
	name: string;
	date: string;
	warmUpTime: string;
	startTime: string;
	eventCount: number;
}

export default function SessionsPage() {
	const [mappedSessions, setMappedSessions] = useState<Session[]>([]);
	const [loading, setLoading] = useState(true);

	// Mock meets for now, eventually fetch from backend
	const meets = [{ id: "1", name: "Summer Championships" }];

	useEffect(() => {
		getSessions()
			.then((response: any) => {
				if (response?.sessions) {
					const mapped = response.sessions.map((s: ServerSession) => ({
						id: s.id,
						meetId: s.meetId,
						name: s.name,
						date: s.date,
						warmUpTime: s.warmUpTime,
						startTime: s.startTime,
						eventCount: s.eventCount,
					}));
					setMappedSessions(mapped);
				}
			})
			.catch((e) => console.error("Failed to fetch sessions", e))
			.finally(() => setLoading(false));
	}, []);

	return (
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<div className="flex-1 flex flex-col overflow-hidden">
					<div className="p-6 pb-0">
						<h1 className="text-2xl font-bold text-foreground">Sessions</h1>
						<p className="text-muted-foreground">
							Manage meet sessions and schedules
						</p>
					</div>
					{loading ? (
						<div className="flex-1 flex items-center justify-center p-6">
							<span className="text-muted-foreground animate-pulse">
								Loading sessions...
							</span>
						</div>
					) : (
						<SessionsManager initialSessions={mappedSessions} meets={meets} />
					)}
				</div>
			</SidebarInset>
		</>
	);
}
