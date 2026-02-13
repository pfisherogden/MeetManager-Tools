import { ArrowLeft, MapPin } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTeam } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";

export const dynamic = "force-dynamic";

export default async function TeamPage({
	params,
}: {
	params: Promise<{ id: string }>;
}) {
	const resolvedParams = await params;
	const { id } = resolvedParams;
	const teamId = parseInt(id, 10);

	let team: any = null;
	try {
		const response = await getTeam(teamId);
		team = response.team;
	} catch (e) {
		console.error("Failed to load team", e);
	}

	if (!team || !team.id) {
		return notFound();
	}

	return (
		<SidebarProvider>
			<AppSidebar />
			<main className="flex-1 flex flex-col min-h-screen bg-background">
				<div className="p-4 border-b flex items-center gap-4">
					<SidebarTrigger />
					<div className="flex items-center gap-4">
						<Link
							href="/teams"
							className="text-muted-foreground hover:text-foreground flex items-center gap-1"
						>
							<ArrowLeft className="h-4 w-4" />
							Back to Teams
						</Link>
					</div>
				</div>

				<div className="p-6 max-w-4xl w-full mx-auto space-y-6">
					<div>
						<h1 className="text-3xl font-bold">{team.name}</h1>
						<div className="flex items-center gap-2 mt-2 text-muted-foreground">
							<MapPin className="h-4 w-4" />
							<span>
								{team.city}, {team.state}
							</span>
						</div>
					</div>

					<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
						<div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm">
							<h2 className="text-lg font-semibold mb-4">Team Details</h2>
							<dl className="space-y-4">
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">
										Abbreviation
									</dt>
									<dd className="font-mono bg-muted px-2 py-0.5 rounded text-sm">
										{team.code}
									</dd>
								</div>
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">LSC</dt>
									<dd>{team.lsc || "-"}</dd>
								</div>
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">
										Athlete Count
									</dt>
									<dd>{team.athleteCount}</dd>
								</div>
							</dl>
						</div>
					</div>
				</div>
			</main>
		</SidebarProvider>
	);
}
