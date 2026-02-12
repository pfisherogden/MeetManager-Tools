"use client";

// ... imports
import { useMemo, useState } from "react";
import { type Column, DataTable } from "@/components/data-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { EventScore, Score } from "@/lib/swim-meet-types";

// Placeholder for fetching full metadata if needed, but currently unused for options
// const teams = ...
// const meets = ...

// Helper for meet names if we had a meet list.
// For now, identity or simple formatting if we don't have the list.
const _getMeetName = (meetId: string) => meetId;

interface ScoresManagerProps {
	initialScores: Score[];
	initialEventScores?: EventScore[];
}

export function ScoresManager({
	initialScores,
	initialEventScores = [],
}: ScoresManagerProps) {
	const [data, setData] = useState<Score[]>(initialScores);

	// Flatten event scores for table
	const eventRows = useMemo(
		() =>
			initialEventScores
				.flatMap((ev) =>
					ev.entries.map((e) => ({
						id: `ev-${ev.eventId}-${e.id}-${e.place}`, // unique key
						eventName: ev.eventName,
						place: e.place,
						athleteName: e.athleteName || "Relay Team",
						teamName: e.teamName,
						seedTime: e.seedTime,
						finalTime: e.finalTime,
						heat: e.heat,
						lane: e.lane,
						points: e.points,
					})),
				)
				.sort((a, b) => {
					if (a.eventName === b.eventName)
						return (a.place || 999) - (b.place || 999);
					return a.eventName.localeCompare(b.eventName);
				}),
		[initialEventScores],
	);

	const columns = useMemo<Column<Score>[]>(() => {
		const uniqueTeams = Array.from(new Set(data.map((d) => d.teamName))).sort();
		const uniqueMeets = Array.from(new Set(data.map((d) => d.meetName))).sort();
		const uniqueRanks = Array.from(new Set(data.map((d) => d.rank))).sort(
			(a, b) => a - b,
		);

		return [
			{
				key: "rank",
				label: "Rank",
				editable: true,
				type: "number",
				filterVariant: "faceted",
				options: uniqueRanks.map(String),
				width: "w-20",
				render: (value) => {
					const rank = value as number;
					const colors = {
						1: "bg-sunshine text-foreground font-bold",
						2: "bg-gray-200 text-gray-800",
						3: "bg-lane-red/30 text-lane-red",
					};
					return (
						<span
							className={`inline-flex w-8 h-8 items-center justify-center rounded-full text-sm ${
								colors[rank as keyof typeof colors] ||
								"bg-muted text-muted-foreground"
							}`}
						>
							{rank}
						</span>
					);
				},
			},
			{
				key: "teamName",
				label: "Team",
				editable: true,
				type: "select",
				filterVariant: "faceted",
				options: uniqueTeams,
				width: "w-48",
				render: (value) => {
					// Removed color lookup as we lack team metadata list.
					// Could inject colors if `data` had it or via another prop.
					return (
						<div className="flex items-center gap-2">
							<span className="font-medium">{value as string}</span>
						</div>
					);
				},
			},
			{
				key: "meetName",
				label: "Meet",
				editable: false,
				type: "select",
				filterVariant: "faceted",
				options: uniqueMeets,
				width: "w-48",
				render: (value) => (
					<span className="font-medium">{value as string}</span>
				),
			},
			{
				key: "individualPoints",
				label: "Individual",
				editable: true,
				type: "number",
				width: "w-28",
				render: (value) => <span className="font-mono">{value as number}</span>,
			},
			{
				key: "relayPoints",
				label: "Relay",
				editable: true,
				type: "number",
				width: "w-24",
				render: (value) => <span className="font-mono">{value as number}</span>,
			},
			{
				key: "totalPoints",
				label: "Total",
				editable: true,
				type: "number",
				width: "w-28",
				render: (value) => (
					<span className="font-mono font-bold text-pool-blue">
						{value as number}
					</span>
				),
			},
		];
	}, [data]);

	const eventColumns = useMemo<Column<any>[]>(() => {
		const uniqueEvents = Array.from(
			new Set(eventRows.map((r) => r.eventName)),
		).sort();
		const uniqueTeams = Array.from(
			new Set(eventRows.map((r) => r.teamName)),
		).sort();
		const uniqueRanks = Array.from(new Set(eventRows.map((r) => r.place))).sort(
			(a, b) => (Number(a) || 999) - (Number(b) || 999),
		);

		return [
			{
				key: "eventName",
				label: "Event",
				editable: false,
				width: "w-48",
				filterVariant: "faceted",
				options: uniqueEvents,
			},
			{
				key: "place",
				label: "Rank",
				editable: false,
				width: "w-16",
				type: "number",
				filterVariant: "faceted",
				options: uniqueRanks.map(String),
			},
			{
				key: "athleteName",
				label: "Athlete / Relay",
				editable: false,
				width: "w-48",
			},
			{
				key: "teamName",
				label: "Team",
				editable: false,
				width: "w-32",
				filterVariant: "faceted",
				options: uniqueTeams,
			},
			{
				key: "heat",
				label: "Heat",
				editable: false,
				width: "w-16",
				type: "number",
			},
			{
				key: "lane",
				label: "Lane",
				editable: false,
				width: "w-16",
				type: "number",
			},
			{ key: "seedTime", label: "Seed", editable: false, width: "w-24" },
			{ key: "finalTime", label: "Time", editable: false, width: "w-24" },
			{
				key: "points",
				label: "Points",
				editable: false,
				width: "w-20",
				type: "number",
			},
		];
	}, [eventRows]);

	const handleAdd = () => {
		const newScore: Score = {
			id: `sc${Date.now()}`,
			meetId: "1",
			meetName: "Unknown Meet",
			teamId: "0",
			teamName: "New Team",
			individualPoints: 0,
			relayPoints: 0,
			totalPoints: 0,
			rank: data.length + 1,
		};
		setData([newScore, ...data]);
	};

	const handleDelete = (id: string) => {
		setData(data.filter((s) => s.id !== id));
	};

	const handleUpdate = (
		id: string,
		key: keyof Score,
		value: Score[keyof Score],
	) => {
		setData(
			data.map((s) => {
				if (s.id !== id) return s;
				const updated = { ...s, [key]: value };
				// Note: teamId update logic removed as we don't have full team list map here
				if (key === "individualPoints" || key === "relayPoints") {
					updated.totalPoints =
						Number(updated.individualPoints) + Number(updated.relayPoints);
				}
				return updated;
			}),
		);
	};

	return (
		<div className="flex-1 p-6 pt-4">
			<div className="h-full rounded-xl border border-border bg-card overflow-hidden shadow-sm">
				<Tabs defaultValue="team">
					<TabsList>
						<TabsTrigger value="team">Team Scores</TabsTrigger>
						<TabsTrigger value="events">Event Results</TabsTrigger>
					</TabsList>
					<TabsContent value="team" className="h-full">
						<div className="h-full rounded-xl border border-border bg-card overflow-hidden shadow-sm">
							<DataTable
								data={data}
								columns={columns}
								onAdd={handleAdd}
								onDelete={handleDelete}
								onUpdate={handleUpdate}
							/>
						</div>
					</TabsContent>
					<TabsContent value="events" className="h-full">
						<div className="h-full rounded-xl border border-border bg-card overflow-hidden shadow-sm">
							<DataTable data={eventRows} columns={eventColumns} />
						</div>
					</TabsContent>
				</Tabs>
			</div>
		</div>
	);
}
