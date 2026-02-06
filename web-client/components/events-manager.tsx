"use client"

import { useState } from "react"
import { DataTable, type Column } from "@/components/data-table"
import type { SwimEvent } from "@/lib/swim-meet-types"
import Link from "next/link"

// ToDo: Fetch sessions from API
const sessions = [{ id: "1", name: "Session 1" }, { id: "2", name: "Session 2" }]
const getSessionName = (sessionId: string) => sessions.find(s => s.id === sessionId)?.name || sessionId

const columns: Column<SwimEvent>[] = [
    { key: "eventNumber", label: "Event #", editable: true, type: "number", width: "w-20" },
    {
        key: "sessionId",
        label: "Session",
        editable: true,
        type: "select",
        options: sessions.map(s => s.id),
        width: "w-36",
        filterVariant: "faceted",
        render: (value) => (
            <Link href={`/sessions/${value}`} className="hover:underline text-primary">
                {getSessionName(value as string)}
            </Link>
        )
    },
    { key: "distance", label: "Distance", editable: true, type: "number", width: "w-24" },
    {
        key: "stroke",
        label: "Stroke",
        editable: true,
        type: "select",
        options: ["Freestyle", "Backstroke", "Breaststroke", "Butterfly", "IM"],
        width: "w-32",
        filterVariant: "faceted",
        render: (value) => {
            const stroke = value as string
            const colors: Record<string, string> = {
                Freestyle: "bg-pool-blue/20 text-pool-blue",
                Backstroke: "bg-sunshine/30 text-foreground",
                Breaststroke: "bg-lane-red/20 text-lane-red",
                Butterfly: "bg-pool-light/50 text-foreground",
                IM: "bg-muted text-foreground",
                "Medley Relay": "bg-purple-100 text-purple-700",
                "Free Relay": "bg-green-100 text-green-700",
            }
            // Simple fallback color if not found
            const colorClass = colors[stroke] || "bg-muted text-muted-foreground"

            return (
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
                    {stroke}
                </span>
            )
        }
    },
    {
        key: "gender",
        label: "Gender",
        editable: true,
        type: "select",
        options: ["M", "F", "Mixed", "Boys", "Girls", "Men", "Women"],
        filterVariant: "faceted",
        width: "w-24"
    },
    { key: "ageGroup", label: "Age Group", editable: true, width: "w-24", filterVariant: "faceted" },
    { key: "entryCount", label: "Entries", editable: true, type: "number", width: "w-20" },
]

interface EventsManagerProps {
    initialEvents: SwimEvent[]
}

export function EventsManager({ initialEvents }: EventsManagerProps) {
    const [data, setData] = useState<SwimEvent[]>(initialEvents)

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
        }
        setData([newEvent, ...data])
    }

    const handleDelete = (id: string) => {
        setData(data.filter((e) => e.id !== id))
    }

    const handleUpdate = (id: string, key: keyof SwimEvent, value: SwimEvent[keyof SwimEvent]) => {
        setData(data.map((e) => (e.id === id ? { ...e, [key]: value } : e)))
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
