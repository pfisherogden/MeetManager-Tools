import { AppSidebar } from "@/components/app-sidebar"
import client from "@/lib/mm-client";
import { AthleteRequest } from "@/lib/proto/meet_manager";
import { notFound } from "next/navigation";
import Link from "next/link";

export const dynamic = 'force-dynamic';

export default async function AthletePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const athleteId = parseInt(id);

    const athlete = await new Promise<any>((resolve) => {
        client.getAthlete(AthleteRequest.fromPartial({ id: athleteId }), (err, response) => {
            if (err) {
                console.error("Error fetching athlete:", err);
                resolve(null);
            }
            else resolve(response);
        });
    });

    if (!athlete || !athlete.id) {
        return notFound();
    }

    return (
        <div className="flex min-h-screen bg-background">
            <AppSidebar />
            <main className="flex-1 p-6">
                <div className="flex items-center gap-4 mb-6">
                    <Link href="/athletes" className="text-muted-foreground hover:text-foreground">
                        ← Back to Athletes
                    </Link>
                </div>
                <div className="space-y-6">
                    <div>
                        <h1 className="text-3xl font-bold">{athlete.firstName} {athlete.lastName}</h1>
                        <p className="text-xl text-muted-foreground">
                            Athlete #{athlete.id}
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="p-6 rounded-xl border bg-card">
                            <h2 className="text-lg font-semibold mb-4">Profile</h2>
                            <dl className="space-y-2">
                                <div className="flex justify-between border-b pb-2">
                                    <dt className="text-muted-foreground">Team</dt>
                                    <dd>
                                        <Link href={`/teams/${athlete.teamId}`} className="text-primary hover:underline">
                                            {athlete.teamName || "Unattached"}
                                        </Link>
                                    </dd>
                                </div>
                                <div className="flex justify-between border-b pb-2">
                                    <dt className="text-muted-foreground">Gender</dt>
                                    <dd>{athlete.gender}</dd>
                                </div>
                                <div className="flex justify-between border-b pb-2">
                                    <dt className="text-muted-foreground">Age</dt>
                                    <dd>{athlete.age}</dd>
                                </div>
                                <div className="flex justify-between border-b pb-2">
                                    <dt className="text-muted-foreground">School Year</dt>
                                    <dd>{athlete.schoolYear}</dd>
                                </div>
                                <div className="flex justify-between pt-2">
                                    <dt className="text-muted-foreground">Registration</dt>
                                    <dd className="font-mono text-sm">{athlete.regNo}</dd>
                                </div>
                            </dl>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}
