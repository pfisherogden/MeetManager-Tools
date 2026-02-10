"use client"

import {
  Trophy,
  Users,
  Calendar,
  Timer,
  User,
  ClipboardList,
  GitBranch,
  Medal,
  LayoutDashboard,
  Waves,
  FileText,
} from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { useConfig } from "@/components/config-provider"

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Meets", href: "/meets", icon: Trophy },
  { name: "Teams", href: "/teams", icon: Users },
  { name: "Sessions", href: "/sessions", icon: Calendar },
  { name: "Events", href: "/events", icon: Timer },
  { name: "Athletes", href: "/athletes", icon: User },
  { name: "Entries", href: "/entries", icon: ClipboardList },
  { name: "Relays", href: "/relays", icon: GitBranch },
  { name: "Scores", href: "/scores", icon: Medal },
  { name: "Reports", href: "/reports", icon: FileText },
  { name: "Admin", href: "/admin", icon: ClipboardList }, // Temporary icon
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 bg-sidebar text-sidebar-foreground flex flex-col h-screen border-r border-sidebar-border">
      {/* Logo */}
      <div className="p-6 border-b border-sidebar-border">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-sidebar-primary flex items-center justify-center">
            <Waves className="h-6 w-6 text-sidebar-primary-foreground" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-sidebar-foreground">SwimMeet Pro</h1>
            <p className="text-xs text-sidebar-foreground/60">Data Management</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-md"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border">
        <SidebarFooterContent />
      </div>
    </aside>
  )
}

function SidebarFooterContent() {
  const { meetDescription } = useConfig();
  if (!meetDescription) return null;

  // Split optionally by first newline or just show it
  return (
    <div className="px-4 py-3 rounded-lg bg-sidebar-accent/50 space-y-2">
      <p className="text-xs text-sidebar-foreground/60 whitespace-pre-wrap">
        {meetDescription}
      </p>
      {process.env.NEXT_PUBLIC_BUILD_TIME && (
        <div className="text-[10px] text-sidebar-foreground/30 font-mono pt-2 border-t border-sidebar-border/50">
          Build: {new Date(process.env.NEXT_PUBLIC_BUILD_TIME).toLocaleString()}
        </div>
      )}
    </div>
  )
}
