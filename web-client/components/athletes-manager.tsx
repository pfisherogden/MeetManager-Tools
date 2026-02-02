"use client"

import { useState } from "react"
import { DataTable, type Column } from "@/components/data-table"
import type { Athlete, Team } from "@/lib/swim-meet-types"

const columns: Column<Athlete>[] = [
    { key: "firstName", label: "First Name", editable: true, width: "w-32" },
    { key: "lastName", label: "Last Name", editable: true, width: "w-32" },
    {
        key: "teamName",
        label: "Team",
        editable: true,
        type: "select",
        // Note: In a real app we might pass team options as props too
        options: ["Kyleton Swimmers", "Other"],
        width: "w-44",
        render: (value) => (
            <div className="flex items-center gap-2">
                {/* Simplification: removed color dot for now as we need team metadata lookup */}
                <span>{value as string}</span>
            </div>
        )
    },
    { key: "dateOfBirth", label: "Birth Date", editable: true, type: "date", width: "w-32" },
    { key: "age", label: "Age", editable: true, type: "number", width: "w-16" },
    {
        key: "gender",
        label: "Gender",
        editable: true,
        type: "select",
        options: ["M", "F"],
        width: "w-20",
        render: (value) => (
            <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${value === "F" ? "bg-pink-100 text-pink-700" : "bg-blue-100 text-blue-700"
                }`}>
                {value === "F" ? "Female" : "Male"}
            </span>
        )
    },
]

interface AthletesManagerProps {
    initialAthletes: Athlete[];
}

export function AthletesManager({ initialAthletes }: AthletesManagerProps) {
    const [data, setData] = useState<Athlete[]>(initialAthletes)

    const handleAdd = () => {
        const newAthlete: Athlete = {
            id: `a${Date.now()}`,
            firstName: "New",
            lastName: "Athlete",
            teamId: "",
            teamName: "Kyleton Swimmers",
            dateOfBirth: "2010-01-01",
            gender: "F",
            age: 12,
        }
        setData([newAthlete, ...data])
    }

    const handleDelete = (id: string) => {
        setData(data.filter((a) => a.id !== id))
    }

    const handleUpdate = (id: string, key: keyof Athlete, value: Athlete[keyof Athlete]) => {
        setData(data.map((a) => {
            if (a.id !== id) return a
            return { ...a, [key]: value }
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
