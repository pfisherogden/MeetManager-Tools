"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { type Column, DataTable } from "@/components/data-table";
import type { Session, SwimEvent } from "@/lib/swim-meet-types";

interface EventsManagerProps {
	initialEvents: SwimEvent[];
	sessions: Session[];
}

export function EventsManager({ initialEvents, sessions }: EventsManagerProps) {
	const searchParams = useSearchParams();
	const sessionFilter = searchParams.get("session");

	const getSessionName = (sessionId: string) =>
		sessions.find((s) => s.id === sessionId)?.name || `Session ${sessionId}`;

	// Filter initial data based on URL params
	const filteredInitial = sessionFilter
		? initialEvents.filter((e) => e.sessionId === sessionFilter)
		: initialEvents;

	const [data, setData] = useState<SwimEvent[]>(filteredInitial);

	const columns: Column<SwimEvent>[] = [
		{
			key: "eventNumber",
			label: "Event #",
			editable: true,
			type: "number",
			width: "w-20",
		},
		{
			key: "sessionId",
			label: "Session",
			editable: true,
			type: "select",
			options: sessions.map((s) => s.id),
			width: "w-36",
			filterVariant: "faceted",
			render: (value) => (
				<Link
					href={`/sessions/${value}`}
					className="hover:underline text-primary"
				>
					{getSessionName(value as string)}
				</Link>
			),
		},
		{
			key: "distance",
			label: "Distance",
			editable: true,
			type: "number",
			width: "w-24",
		},
		{
			key: "stroke",
			label: "Stroke",
			editable: true,
			type: "select",
			options: ["Freestyle", "Backstroke", "Breaststroke", "Butterfly", "IM"],
			width: "w-32",
			filterVariant: "faceted",
			render: (value) => {
				const stroke = value as string;
				const colors: Record<string, string> = {
					Freestyle: "bg-pool-blue/20 text-pool-blue border-pool-blue/30",
					Free: "bg-pool-blue/20 text-pool-blue border-pool-blue/30",
					Backstroke:
						"bg-sunshine/20 text-sunshine-foreground border-sunshine/30",
					Back: "bg-sunshine/20 text-sunshine-foreground border-sunshine/30",
					Breaststroke: "bg-lane-red/20 text-lane-red border-lane-red/30",
					Breast: "bg-lane-red/20 text-lane-red border-lane-red/30",
					Butterfly: "bg-indigo-100 text-indigo-700 border-indigo-200",
					Fly: "bg-indigo-100 text-indigo-700 border-indigo-200",
					IM: "bg-purple-100 text-purple-700 border-purple-200",
					Relay: "bg-emerald-100 text-emerald-700 border-emerald-200",
					"Medley Relay": "bg-emerald-100 text-emerald-700 border-emerald-200",
					"Free Relay": "bg-emerald-100 text-emerald-700 border-emerald-200",
				};

				// Standardize search
				const matchedKey = Object.keys(colors).find((k) =>
					stroke.toLowerCase().includes(k.toLowerCase()),
				);

				const colorClass = matchedKey
					? colors[matchedKey]
					: "bg-muted text-muted-foreground border-border";

				return (
					<span
						className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold border tracking-wider uppercase ${colorClass}`}
					>
						{stroke}
					</span>
				);
			},
		},
		{
			key: "gender",
			label: "Gender",
			editable: true,
			type: "select",
			options: ["M", "F", "Mixed", "Boys", "Girls", "Men", "Women"],
			filterVariant: "faceted",
			width: "w-24",
		},
		{
			key: "ageGroup",
			label: "Age Group",
			editable: true,
			width: "w-24",
			filterVariant: "faceted",
		},
		{
			key: "entryCount",
			label: "Entries",
			editable: false,
			width: "w-24",
			render: (value, row) => (
				<Link
					href={
						row.isRelay ? `/relays?event=${row.id}` : `/entries?event=${row.id}`
					}
					className="flex items-center gap-2 group"
				>
					<div className="relative w-8 h-8 flex items-center justify-center">
						<div className="absolute inset-0 rounded-full border-2 border-muted" />
						<div
							className="absolute inset-0 rounded-full border-t-2 border-primary"
							style={{ transform: "rotate(-45deg)" }}
						/>
						<span className="text-xs font-medium">{value as number}</span>
					</div>
					<span className="text-xs text-muted-foreground group-hover:text-primary transition-colors">
						View
					</span>
				</Link>
			),
		},
	];

	const handleAdd = () => {
		const newEvent: SwimEvent = {
			id: `e${Date.now()}`,
			sessionId: sessions[0]?.id || "",
			eventNumber: data.length + 1,
			distance: 100,
			stroke: "Freestyle",
			gender: "F",
			ageGroup: "Open",
			entryCount: 0,
		};
		setData([newEvent, ...data]);
	};

	const handleDelete = (id: string) => {
		setData(data.filter((e) => e.id !== id));
	};

	const handleUpdate = (
		id: string,
		key: keyof SwimEvent,
		value: SwimEvent[keyof SwimEvent],
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
