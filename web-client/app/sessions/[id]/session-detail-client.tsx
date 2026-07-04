"use client";

import Link from "next/link";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

export function SessionDetailClient({ id }: { id: string }) {
	return (
		<>
			<AppSidebar />
			<SidebarInset className="flex flex-col">
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
					<SidebarTrigger className="-ml-1" />
					<div className="flex items-center gap-4">
						<Link
							href="/events"
							className="text-muted-foreground hover:text-foreground flex items-center gap-1"
						>
							Back to Events
						</Link>
					</div>
				</header>
				<div className="flex-1 p-6">
					<div className="space-y-6">
						<div>
							<h1 className="text-3xl font-bold">Session {id}</h1>
							<p className="text-xl text-muted-foreground">
								Details for specific sessions are not yet implemented.
							</p>
						</div>
					</div>
				</div>
			</SidebarInset>
		</>
	);
}
