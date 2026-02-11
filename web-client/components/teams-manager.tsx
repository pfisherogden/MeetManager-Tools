"use client";

import Link from "next/link";
import { useState } from "react";
import { type Column, DataTable } from "@/components/data-table";
import type { Team } from "@/lib/swim-meet-types";

const columns: Column<Team>[] = [
	{
		key: "name",
		label: "Team Name",
		editable: true,
		width: "w-52",
		render: (value, row) => (
			<Link
				href={`/teams/${row.id}`}
				className="hover:underline text-primary font-medium"
			>
				{value as string}
			</Link>
		),
	},
	{ key: "abbreviation", label: "Abbr", editable: true, width: "w-20" },
	{ key: "city", label: "City", editable: true, width: "w-36" },
	{
		key: "state",
		label: "State",
		editable: true,
		width: "w-20",
		filterVariant: "faceted",
	},
	{
		key: "athleteCount",
		label: "Athletes",
		editable: true,
		type: "number",
		width: "w-24",
		render: (value, row) => (
			<Link
				href={`/athletes?teamId=${row.id}`}
				className="hover:underline text-primary font-medium"
			>
				{value as number}
			</Link>
		),
	},
	{
		key: "color",
		label: "Color",
		editable: true,
		width: "w-28",
		render: (value) => (
			<div className="flex items-center gap-2">
				<span
					className="w-4 h-4 rounded-full border border-border"
					style={{ backgroundColor: value as string }}
				/>
				<span className="font-mono text-xs">{value as string}</span>
			</div>
		),
	},
];

interface TeamsManagerProps {
	initialTeams: Team[];
}

export function TeamsManager({ initialTeams }: TeamsManagerProps) {
	const [data, setData] = useState<Team[]>(initialTeams);

	const handleAdd = () => {
		const newTeam: Team = {
			id: `t${Date.now()}`,
			name: "New Team",
			abbreviation: "NEW",
			city: "",
			state: "",
			athleteCount: 0,
			color: "#0077B6",
		};
		setData([newTeam, ...data]);
	};

	const handleDelete = (id: string) => {
		setData(data.filter((t) => t.id !== id));
	};

	const handleUpdate = (
		id: string,
		key: keyof Team,
		value: Team[keyof Team],
	) => {
		setData(data.map((t) => (t.id === id ? { ...t, [key]: value } : t)));
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
