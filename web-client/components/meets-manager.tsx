"use client"

import { useState } from "react"
import { DataTable, type Column } from "@/components/data-table"
import type { Meet } from "@/lib/swim-meet-types"

const columns: Column<Meet>[] = [
    { key: "name", label: "Meet Name", editable: true, width: "w-64" },
    { key: "location", label: "Location", editable: true, width: "w-56" },
    { key: "startDate", label: "Start Date", editable: true, type: "date", width: "w-32" },
    { key: "endDate", label: "End Date", editable: true, type: "date", width: "w-32" },
    { key: "poolType", label: "Course", editable: true, type: "select", options: ["SCY", "SCM", "LCM"], width: "w-24" },
    {
        key: "status",
        label: "Status",
        editable: true,
        type: "select",
        options: ["upcoming", "active", "completed"],
        width: "w-28",
        render: (value) => {
            const status = value as Meet["status"]
            return (
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${status === "active" ? "bg-lane-red/20 text-lane-red" :
                        status === "upcoming" ? "bg-sunshine/30 text-foreground" :
                            "bg-muted text-muted-foreground"
                    }`}>
                    {status}
                </span>
            )
        }
    },
]

interface MeetsManagerProps {
    initialMeets: Meet[]
}

export function MeetsManager({ initialMeets }: MeetsManagerProps) {
    const [data, setData] = useState<Meet[]>(initialMeets)

    const handleAdd = () => {
        const newMeet: Meet = {
            id: `m${Date.now()}`,
            name: "New Meet",
            location: "",
            startDate: new Date().toISOString().split("T")[0],
            endDate: new Date().toISOString().split("T")[0],
            poolType: "SCY",
            status: "upcoming",
        }
        setData([newMeet, ...data])
    }

    const handleDelete = (id: string) => {
        setData(data.filter((m) => m.id !== id))
    }

    const handleUpdate = (id: string, key: keyof Meet, value: Meet[keyof Meet]) => {
        setData(data.map((m) => (m.id === id ? { ...m, [key]: value } : m)))
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
