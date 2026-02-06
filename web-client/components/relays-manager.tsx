"use client"

import { useState } from "react"
import { DataTable, type Column } from "@/components/data-table"
import type { Relay } from "@/lib/swim-meet-types"

// ToDo: fetch teams from API
const teams = [{ id: "1", name: "Team A", color: "#FF0000" }, { id: "2", name: "Team B", color: "#00FF00" }]

const columns: Column<Relay>[] = [
    {
        key: "teamName",
        label: "Team",
        editable: true,
        type: "select",
        options: teams.map(t => t.name),
        width: "w-44",
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
    { key: "eventId", label: "Event", editable: true, width: "w-20", filterVariant: "faceted" }, // Added filterVariant
    { key: "leg1", label: "Leg 1", editable: true, width: "w-36" },
    { key: "leg2", label: "Leg 2", editable: true, width: "w-36" },
    { key: "leg3", label: "Leg 3", editable: true, width: "w-36" },
    { key: "leg4", label: "Leg 4", editable: true, width: "w-36" },
    {
        key: "seedTime",
        label: "Seed",
        editable: true,
        width: "w-24",
        render: (value) => (
            <span className="font-mono text-sm">{value as string}</span>
        )
    },
    {
        key: "finalTime",
        label: "Final",
        editable: true,
        width: "w-24",
        render: (value) => (
            <span className={`font-mono text-sm ${value ? "text-foreground" : "text-muted-foreground"}`}>
                {value as string || "—"}
            </span>
        )
    },
    {
        key: "place",
        label: "Place",
        editable: true,
        type: "number",
        width: "w-20",
        render: (value) => {
            const place = value as number | null
            if (!place) return <span className="text-muted-foreground">—</span>
            const colors = {
                1: "bg-sunshine text-foreground",
                2: "bg-gray-200 text-gray-800",
                3: "bg-lane-red/30 text-lane-red",
            }
            return (
                <span className={`inline-flex w-6 h-6 items-center justify-center rounded-full text-xs font-bold ${colors[place as keyof typeof colors] || "bg-muted text-muted-foreground"
                    }`}>
                    {place}
                </span>
            )
        }
    },
]

interface RelaysManagerProps {
    initialRelays: Relay[]
}

export function RelaysManager({ initialRelays }: RelaysManagerProps) {
    const [data, setData] = useState<Relay[]>(initialRelays)

    const handleAdd = () => {
        const newRelay: Relay = {
            id: `r${Date.now()}`,
            eventId: "",
            teamId: teams[0]?.id || "",
            teamName: teams[0]?.name || "",
            leg1: "",
            leg2: "",
            leg3: "",
            leg4: "",
            seedTime: "NT",
            finalTime: null,
            place: null,
        }
        setData([newRelay, ...data])
    }

    const handleDelete = (id: string) => {
        setData(data.filter((r) => r.id !== id))
    }

    const handleUpdate = (id: string, key: keyof Relay, value: Relay[keyof Relay]) => {
        setData(data.map((r) => {
            if (r.id !== id) return r
            const updated = { ...r, [key]: value }
            if (key === "teamName") {
                const team = teams.find(t => t.name === value)
                if (team) updated.teamId = team.id
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
