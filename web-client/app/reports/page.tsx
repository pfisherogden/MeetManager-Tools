import { AppSidebar } from "@/components/app-sidebar";
import { ReportsManager } from "@/components/reports-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

export const dynamic = "force-dynamic";

export default async function ReportsPage() {
	return (
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<div className="flex-1 flex flex-col overflow-hidden">
					<div className="p-6 pb-0">
						<h1 className="text-2xl font-bold">Reports</h1>
						<p className="text-muted-foreground">
							Generate and customize PDF reports from meet data
						</p>
					</div>
					<ReportsManager />
				</div>
			</SidebarInset>
		</>
	);
}
