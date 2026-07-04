import { SessionDetailClient } from "./session-detail-client";

export default async function SessionPage({
	params,
}: {
	params: Promise<{ id: string }>;
}) {
	const { id } = await params;
	return <SessionDetailClient id={id} />;
}

export async function generateStaticParams() {
	return [{ id: "1" }];
}
