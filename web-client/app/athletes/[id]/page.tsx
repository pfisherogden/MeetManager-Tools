import { AthleteDetailClient } from "./athlete-detail-client";

export default async function AthletePage({
	params,
}: {
	params: Promise<{ id: string }>;
}) {
	const { id } = await params;
	return <AthleteDetailClient id={id} />;
}

export async function generateStaticParams() {
	return [{ id: "1" }];
}
