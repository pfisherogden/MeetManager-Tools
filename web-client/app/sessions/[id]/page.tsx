import Link from "next/link";
import { AppSidebar } from "@/components/app-sidebar";

export default async function SessionPage({
	params,
}: {
	params: Promise<{ id: string }>;
}) {
	const { id } = await params;

	return (
		<div className="flex min-h-screen bg-background">
			<AppSidebar />
			<main className="flex-1 p-6">
				<div className="flex items-center gap-4 mb-6">
					<Link
						href="/events"
						className="text-muted-foreground hover:text-foreground"
					>
						← Back to Events
					</Link>
				</div>
				<div className="space-y-6">
					<div>
						<h1 className="text-3xl font-bold">Session {id}</h1>
						<p className="text-xl text-muted-foreground">
							Details for specific sessions are not yet implemented.
						</p>
					</div>
				</div>
			</main>
		</div>
	);
}
