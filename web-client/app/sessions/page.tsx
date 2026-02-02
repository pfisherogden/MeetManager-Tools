"use client"

import { useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { DataTable, type Column } from "@/components/data-table"
import { sessions as initialSessions, meets } from "@/lib/swim-meet-data"
import type { Session } from "@/lib/swim-meet-types"

const getMeetName = (meetId: string) => meets.find(m => m.id === meetId)?.name || meetId

const columns: Column<Session>[] = [
  { key: "name", label: "Session Name", editable: true, width: "w-40" },
  { 
    key: "meetId", 
    label: "Meet", 
    editable: true, 
    type: "select",
    options: meets.map(m => m.id),
    width: "w-52",
    render: (value) => getMeetName(value as string)
  },
  { key: "date", label: "Date", editable: true, type: "date", width: "w-32" },
  { key: "warmUpTime", label: "Warm-up", editable: true, width: "w-24" },
  { key: "startTime", label: "Start", editable: true, width: "w-24" },
  { key: "eventCount", label: "Events", editable: true, type: "number", width: "w-20" },
]

export default function SessionsPage() {
  const [data, setData] = useState<Session[]>(initialSessions)

  const handleAdd = () => {
    const newSession: Session = {
      id: `s${Date.now()}`,
      meetId: meets[0]?.id || "",
      name: "New Session",
      date: new Date().toISOString().split("T")[0],
      warmUpTime: "07:00",
      startTime: "09:00",
      eventCount: 0,
    }
    setData([newSession, ...data])
  }

  const handleDelete = (id: string) => {
    setData(data.filter((s) => s.id !== id))
  }

  const handleUpdate = (id: string, key: keyof Session, value: Session[keyof Session]) => {
    setData(data.map((s) => (s.id === id ? { ...s, [key]: value } : s)))
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 pb-0">
          <h1 className="text-2xl font-bold text-foreground">Sessions</h1>
          <p className="text-muted-foreground">Manage meet sessions and schedules</p>
        </div>
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
      </main>
    </div>
  )
}
