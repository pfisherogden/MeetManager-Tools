import { AppSidebar } from "@/components/app-sidebar";
import { DqList } from "@/components/dq-list";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

export const dynamic = "force-dynamic";

export default function DqsPage() {
	return (
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<div className="flex-1 flex flex-col overflow-hidden">
					<div className="p-6 pb-0">
						<h1 className="text-2xl font-bold">Submitted DQs</h1>
						<p className="text-muted-foreground">
							Review and manage disqualifications synced from the Judge App
						</p>
					</div>
					<DqList />
				</div>
			</SidebarInset>
		</>
	);
}
