"use client";

import Link from "next/link";
import { useState } from "react";
import { type Column, DataTable } from "@/components/data-table";
import type { Session } from "@/lib/swim-meet-types";

// We probably want to look up meets for the filter/select
// But for now, we can just display the ID or pass meets as props if needed.
// Passing meets as props is better.

interface SessionsManagerProps {
	initialSessions: Session[];
	meets?: { id: string; name: string }[];
}

export function SessionsManager({
	initialSessions,
	meets = [],
}: SessionsManagerProps) {
	const [data, _setData] = useState<Session[]>(initialSessions);

	const getMeetName = (meetId: string) =>
		meets.find((m) => m.id === meetId)?.name || meetId;

	const columns: Column<Session>[] = [
		{
			key: "name",
			label: "Session Name",
			editable: false,
			width: "w-40",
			render: (value, row) => (
				<Link
					href={`/events?session=${row.id}`}
					className="hover:underline text-primary"
				>
					{value as string}
				</Link>
			),
		},
		{
			key: "meetId",
			label: "Meet",
			editable: false,
			width: "w-52",
			filterVariant: "faceted",
			render: (value) => getMeetName(value as string),
		},
		{
			key: "date",
			label: "Date",
			editable: false,
			type: "date",
			width: "w-32",
			filterVariant: "faceted",
		},
		{ key: "warmUpTime", label: "Warm-up", editable: false, width: "w-24" },
		{
			key: "startTime",
			label: "Start",
			editable: false,
			width: "w-24",
			filterVariant: "faceted",
		},
		{
			key: "eventCount",
			label: "Events",
			editable: false,
			type: "number",
			width: "w-20",
			render: (value, row) => (
				<Link
					href={`/events?session=${row.id}`}
					className="hover:underline text-primary"
				>
					{value as number}
				</Link>
			),
		},
	];

	// Read only for now as backend doesn't support writing
	return (
		<div className="flex-1 p-6 pt-4">
			<div className="h-full rounded-xl border border-border bg-card overflow-hidden shadow-sm">
				<DataTable data={data} columns={columns} />
			</div>
		</div>
	);
}
