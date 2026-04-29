import { getMeets } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { MeetsManager } from "@/components/meets-manager";
import { SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

export default async function MeetsPage() {
	let mappedMeets: any[] = [];

	try {
		const meetsResponse = await getMeets();
		if (meetsResponse?.meets) {
			mappedMeets = meetsResponse.meets;
		}
	} catch (e) {
		console.error("Failed to fetch meets", e);
	}

	return (
		<>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 md:hidden">
					<SidebarTrigger className="-ml-1" />
				</header>
				<div className="flex-1 overflow-auto">
					<div className="p-6 pb-0">
						<h1 className="text-2xl font-bold text-foreground">Meets</h1>
						<p className="text-muted-foreground">
							Manage swimming meets and competitions
						</p>
						<div
							data-testid="meet-count"
							data-count={mappedMeets.length}
							className="hidden"
						/>
					</div>
					<MeetsManager initialMeets={mappedMeets} />
				</div>
			</SidebarInset>
		</>
	);
}
