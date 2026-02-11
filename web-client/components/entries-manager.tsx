"use client";

import Link from "next/link";
import { useState } from "react";
import { type Column, DataTable } from "@/components/data-table";
import type { Entry } from "@/lib/swim-meet-types";

const columns: Column<Entry>[] = [
	{
		key: "athleteName",
		label: "Athlete",
		editable: true,
		width: "w-40",
		render: (value, row) => (
			<Link
				href={`/athletes/${row.athleteId}`}
				className="hover:underline text-primary font-medium"
			>
				{value as string}
			</Link>
		),
	},
	{
		key: "teamName",
		label: "Team",
		editable: true,
		width: "w-40",
		filterVariant: "faceted",
		render: (value, row) =>
			row.teamId ? (
				<Link
					href={`/teams/${row.teamId}`}
					className="hover:underline text-primary"
				>
					{value as string}
				</Link>
			) : (
				<span>{value as string}</span>
			),
	},
	{
		key: "heat",
		label: "Heat",
		editable: false,
		width: "w-16",
		type: "number",
		filterVariant: "faceted",
	},
	{
		key: "lane",
		label: "Lane",
		editable: false,
		width: "w-16",
		type: "number",
		filterVariant: "faceted",
	},
	{
		key: "eventName",
		label: "Event",
		editable: false,
		width: "w-40",
		filterVariant: "faceted",
	},
	{ key: "eventId", label: "ID", editable: true, width: "w-16" },
	{
		key: "seedTime",
		label: "Seed Time",
		editable: true,
		width: "w-28",
		render: (value) => (
			<span className="font-mono text-sm">{value as string}</span>
		),
	},
	{
		key: "finalTime",
		label: "Final Time",
		editable: true,
		width: "w-28",
		render: (value) => (
			<span
				className={`font-mono text-sm ${value ? "text-foreground" : "text-muted-foreground"}`}
			>
				{(value as string) || "—"}
			</span>
		),
	},
	{
		key: "place",
		label: "Place",
		editable: true,
		type: "number",
		width: "w-20",
		filterVariant: "faceted",
		render: (value) => {
			const place = value as number | null;
			if (!place) return <span className="text-muted-foreground">—</span>;
			const colors = {
				1: "bg-sunshine text-foreground",
				2: "bg-gray-200 text-gray-800",
				3: "bg-lane-red/30 text-lane-red",
			};
			return (
				<span
					className={`inline-flex w-6 h-6 items-center justify-center rounded-full text-xs font-bold ${
						colors[place as keyof typeof colors] ||
						"bg-muted text-muted-foreground"
					}`}
				>
					{place}
				</span>
			);
		},
	},
];

interface EntriesManagerProps {
	initialEntries: Entry[];
}

import { useSearchParams } from "next/navigation";

export function EntriesManager({ initialEntries }: EntriesManagerProps) {
	const searchParams = useSearchParams();
	const eventFilter = searchParams.get("event");

	// Filter initial data based on URL params
	const filteredInitial = eventFilter
		? initialEntries.filter((e) => e.eventId === eventFilter)
		: initialEntries;

	const [data, setData] = useState<Entry[]>(filteredInitial);

	const handleAdd = () => {
		const newEntry: Entry = {
			id: `en${Date.now()}`,
			eventId: "",
			athleteId: "",
			athleteName: "New Athlete",
			teamId: "",
			teamName: "",
			seedTime: "NT",
			finalTime: null,
			place: null,
		};
		setData([newEntry, ...data]);
	};

	const handleDelete = (id: string) => {
		setData(data.filter((e) => e.id !== id));
	};

	const handleUpdate = (
		id: string,
		key: keyof Entry,
		value: Entry[keyof Entry],
	) => {
		setData(data.map((e) => (e.id === id ? { ...e, [key]: value } : e)));
	};

	return (
		<div className="flex-1 p-6 pt-4">
			<div className="h-full rounded-xl border border-border bg-card overflow-hidden shadow-sm">
				<DataTable
					data={data}
					columns={columns}
					onAdd={handleAdd}
					onDelete={handleDelete}
					onUpdate={handleUpdate}
				/>
			</div>
		</div>
	);
}
