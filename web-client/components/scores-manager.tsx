"use client"

import { useState } from "react"
import { DataTable, type Column } from "@/components/data-table"
import type { Score } from "@/lib/swim-meet-types"

// ToDo: fetch teams and meets from API
const teams = [{ id: "1", name: "Team A", color: "#FF0000" }, { id: "2", name: "Team B", color: "#00FF00" }]
const meets = [{ id: "1", name: "Meet 1" }]

const getMeetName = (meetId: string) => meets.find(m => m.id === meetId)?.name || meetId

const columns: Column<Score>[] = [
    {
        key: "rank",
        label: "Rank",
        editable: true,
        type: "number",
        width: "w-20",
        render: (value) => {
            const rank = value as number
            const colors = {
                1: "bg-sunshine text-foreground font-bold",
                2: "bg-gray-200 text-gray-800",
                3: "bg-lane-red/30 text-lane-red",
            }
            return (
                <span className={`inline-flex w-8 h-8 items-center justify-center rounded-full text-sm ${colors[rank as keyof typeof colors] || "bg-muted text-muted-foreground"
                    }`}>
                    {rank}
                </span>
            )
        }
    },
    {
        key: "teamName",
        label: "Team",
        editable: true,
        type: "select",
        options: teams.map(t => t.name),
        width: "w-48",
        render: (value) => {
            const team = teams.find(t => t.name === value)
            return (
                <div className="flex items-center gap-2">
                    {team && (
                        <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: team.color }}
                        />
                    )}
                    <span className="font-medium">{value as string}</span>
                </div>
            )
        }
    },
    {
        key: "meetId",
        label: "Meet",
        editable: true,
        type: "select",
        options: meets.map(m => m.id),
        width: "w-48",
        render: (value) => getMeetName(value as string)
    },
    {
        key: "individualPoints",
        label: "Individual",
        editable: true,
        type: "number",
        width: "w-28",
        render: (value) => (
            <span className="font-mono">{value as number}</span>
        )
    },
    {
        key: "relayPoints",
        label: "Relay",
        editable: true,
        type: "number",
        width: "w-24",
        render: (value) => (
            <span className="font-mono">{value as number}</span>
        )
    },
    {
        key: "totalPoints",
        label: "Total",
        editable: true,
        type: "number",
        width: "w-28",
        render: (value) => (
            <span className="font-mono font-bold text-pool-blue">{value as number}</span>
        )
    },
]

interface ScoresManagerProps {
    initialScores: Score[]
}

export function ScoresManager({ initialScores }: ScoresManagerProps) {
    const [data, setData] = useState<Score[]>(initialScores)

    const handleAdd = () => {
        const newScore: Score = {
            id: `sc${Date.now()}`,
            meetId: meets[0]?.id || "",
            teamId: teams[0]?.id || "",
            teamName: teams[0]?.name || "",
            individualPoints: 0,
            relayPoints: 0,
            totalPoints: 0,
            rank: data.length + 1,
        }
        setData([newScore, ...data])
    }

    const handleDelete = (id: string) => {
        setData(data.filter((s) => s.id !== id))
    }

    const handleUpdate = (id: string, key: keyof Score, value: Score[keyof Score]) => {
        setData(data.map((s) => {
            if (s.id !== id) return s
            const updated = { ...s, [key]: value }
            if (key === "teamName") {
                const team = teams.find(t => t.name === value)
                if (team) updated.teamId = team.id
            }
            if (key === "individualPoints" || key === "relayPoints") {
                updated.totalPoints = Number(updated.individualPoints) + Number(updated.relayPoints)
            }
            return updated
        }))
    }

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
    )
}
