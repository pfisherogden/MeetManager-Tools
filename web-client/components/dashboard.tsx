"use client"
import { Trophy, Users, User, Timer, Calendar, Medal, TrendingUp, Waves } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"
import { DashboardStats } from "@/lib/proto/meet_manager";

interface DashboardProps {
  stats: DashboardStats;
}

import { useConfig } from "@/components/config-provider"

export function Dashboard({ stats: backendStats }: DashboardProps) {
  const { meetName } = useConfig();

  // Use backend stats
  const statItems = [
    {
      name: "Total Meets",
      value: backendStats.meetCount,
      icon: Trophy,
      href: "/meets",
      color: "bg-pool-blue text-tile-white"
    },
    {
      name: "Teams",
      value: backendStats.teamCount,
      icon: Users,
      href: "/teams",
      color: "bg-sunshine text-foreground"
    },
    {
      name: "Athletes",
      value: backendStats.athleteCount,
      icon: User,
      href: "/athletes",
      color: "bg-pool-light text-foreground"
    },
    {
      name: "Events",
      value: backendStats.eventCount,
      icon: Timer,
      href: "/events",
      color: "bg-lane-red text-tile-white"
    },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Welcome to SwimMeet Pro</p>
        </div>
        {meetName && (
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-sunshine/20 text-foreground">
            <Waves className="h-5 w-5 text-pool-blue" />
            <span className="text-sm font-medium">{meetName}</span>
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statItems.map((stat) => (
          <Link key={stat.name} href={stat.href}>
            <Card className="hover:shadow-lg transition-shadow cursor-pointer border-border/50">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.name}</p>
                    <p className="text-3xl font-bold text-foreground mt-1">{stat.value}</p>
                  </div>
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${stat.color}`}>
                    <stat.icon className="h-6 w-6" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Placeholder for future detailed widgets */}
      {/* <div className="p-4 rounded border bg-muted/20 text-center text-muted-foreground">
        Detailed activity widgets coming soon (connected to live data).
      </div> */}
    </div>
  )
}
