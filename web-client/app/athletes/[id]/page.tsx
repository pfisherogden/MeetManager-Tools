import { ArrowLeft, User } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAthlete } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";

export const dynamic = "force-dynamic";

export default async function AthletePage({
	params,
}: {
	params: Promise<{ id: string }>;
}) {
	const { id } = await params;
	const athleteId = parseInt(id, 10);

	let athlete: any = null;
	try {
		athlete = await getAthlete(athleteId);
	} catch (e) {
		console.error("Failed to load athlete", e);
	}

	if (!athlete || !athlete.id) {
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
							href="/athletes"
							className="text-muted-foreground hover:text-foreground flex items-center gap-1"
						>
							<ArrowLeft className="h-4 w-4" />
							Back to Athletes
						</Link>
					</div>
				</div>

				<div className="p-6 max-w-4xl w-full mx-auto space-y-6">
					<div className="flex items-start gap-4">
						<div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
							<User className="h-8 w-8 text-muted-foreground" />
						</div>
						<div>
							<h1 className="text-3xl font-bold">
								{athlete.firstName} {athlete.lastName}
							</h1>
							<div className="flex items-center gap-2 mt-1 text-muted-foreground">
								<Link
									href={`/teams/${athlete.teamId}`}
									className="hover:underline text-primary"
								>
									{athlete.teamName}
								</Link>
							</div>
						</div>
					</div>

					<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
						<div className="p-6 rounded-xl border bg-card text-card-foreground shadow-sm">
							<h2 className="text-lg font-semibold mb-4">Athlete Profile</h2>
							<dl className="space-y-4">
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">Age</dt>
									<dd>{athlete.age}</dd>
								</div>
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">Gender</dt>
									<dd>{athlete.gender}</dd>
								</div>
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">
										School Year
									</dt>
									<dd>{athlete.schoolYear || "-"}</dd>
								</div>
								<div className="flex justify-between border-b pb-2 last:border-0 last:pb-0">
									<dt className="text-muted-foreground font-medium">
										Registration No.
									</dt>
									<dd className="font-mono text-sm uppercase">
										{athlete.regNo || "-"}
									</dd>
								</div>
							</dl>
						</div>
					</div>
				</div>
			</main>
		</SidebarProvider>
	);
}
