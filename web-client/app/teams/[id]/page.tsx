import { AppSidebar } from "@/components/app-sidebar"
import client from "@/lib/mm-client";
import { TeamRequest } from "@/lib/proto/meet_manager";
import { notFound } from "next/navigation";
import Link from "next/link";

export const dynamic = 'force-dynamic';

export default async function TeamPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const teamId = parseInt(id);

    const team = await new Promise<any>((resolve) => {
        client.getTeam(TeamRequest.fromPartial({ id: teamId }), (err, response) => {
            if (err) {
                console.error("Error fetching team:", err);
                resolve(null);
            }
            else resolve(response);
        });
    });

    if (!team || !team.id) {
        return notFound();
    }

    return (
        <div className="flex min-h-screen bg-background">
            <AppSidebar />
            <main className="flex-1 p-6">
                <div className="flex items-center gap-4 mb-6">
                    <Link href="/teams" className="text-muted-foreground hover:text-foreground">
                        ← Back to Teams
                    </Link>
                </div>
                <div className="space-y-6">
                    <div>
                        <h1 className="text-3xl font-bold">{team.name}</h1>
                        <p className="text-xl text-muted-foreground">
                            {team.city}, {team.state}
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="p-6 rounded-xl border bg-card">
                            <h2 className="text-lg font-semibold mb-4">Team Details</h2>
                            <dl className="space-y-2">
                                <div className="flex justify-between border-b pb-2">
                                    <dt className="text-muted-foreground">Abbreviation</dt>
                                    <dd className="font-mono">{team.code}</dd>
                                </div>
                                <div className="flex justify-between border-b pb-2">
                                    <dt className="text-muted-foreground">LSC</dt>
                                    <dd>{team.lsc}</dd>
                                </div>
                                <div className="flex justify-between pt-2">
                                    <dt className="text-muted-foreground">Athlete Count</dt>
                                    <dd>{team.athleteCount}</dd>
                                </div>
                            </dl>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}
