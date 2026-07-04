import { TeamDetailClient } from "./team-detail-client";

export default async function TeamPage({
	params,
}: {
	params: Promise<{ id: string }>;
}) {
	const { id } = await params;
	return <TeamDetailClient id={id} />;
}

export async function generateStaticParams() {
	return [{ id: "1" }];
}
