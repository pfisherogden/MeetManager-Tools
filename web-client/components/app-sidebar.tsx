"use client";

import {
	Calendar,
	ClipboardList,
	FileText,
	GitBranch,
	LayoutDashboard,
	LogOut,
	Medal,
	MoreHorizontal,
	Timer,
	Trophy,
	User,
	Users,
	Waves,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useConfig } from "@/components/config-provider";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	useSidebar,
} from "@/components/ui/sidebar";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

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
];

export function AppSidebar() {
	const pathname = usePathname();
	const { setOpenMobile } = useSidebar();

	return (
		<Sidebar>
			{/* Logo */}
			<SidebarHeader className="p-6 border-b border-sidebar-border">
				<Link href="/" className="flex items-center gap-3">
					<div className="w-10 h-10 rounded-lg bg-sidebar-primary flex items-center justify-center">
						<Waves className="h-6 w-6 text-sidebar-primary-foreground" />
					</div>
					<div>
						<h1 className="font-bold text-lg text-sidebar-foreground">
							SwimMeet Pro
						</h1>
						<p className="text-xs text-sidebar-foreground/60">
							Data Management
						</p>
					</div>
				</Link>
			</SidebarHeader>

			{/* Navigation */}
			<SidebarContent className="p-4">
				<SidebarMenu className="space-y-1">
					{navItems.map((item) => {
						const isActive = pathname === item.href;
						return (
							<SidebarMenuItem key={item.name}>
								<SidebarMenuButton
									asChild
									isActive={isActive}
									tooltip={item.name}
									className={cn(
										"flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 h-auto",
										isActive
											? "bg-sidebar-primary text-sidebar-primary-foreground shadow-md"
											: "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
									)}
								>
									<Link href={item.href} onClick={() => setOpenMobile(false)}>
										<item.icon className="h-5 w-5" />
										<span>{item.name}</span>
									</Link>
								</SidebarMenuButton>
							</SidebarMenuItem>
						);
					})}
				</SidebarMenu>
			</SidebarContent>

			{/* Footer */}
			<SidebarFooter className="p-4 border-t border-sidebar-border space-y-4">
				<UserNav />
				<SidebarFooterContent />
			</SidebarFooter>
		</Sidebar>
	);
}

function UserNav() {
	const { user, logout } = useAuth();

	if (!user) return null;

	const initials = user.displayName
		? user.displayName
				.split(" ")
				.map((n) => n[0])
				.join("")
				.toUpperCase()
		: user.email?.substring(0, 2).toUpperCase() || "U";

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button
					variant="ghost"
					className="w-full justify-start gap-3 px-2 h-12 hover:bg-sidebar-accent"
				>
					<Avatar className="h-8 w-8 border border-sidebar-border shadow-sm">
						<AvatarImage
							src={user.photoURL || ""}
							alt={user.displayName || ""}
						/>
						<AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground text-xs font-bold">
							{initials}
						</AvatarFallback>
					</Avatar>
					<div className="flex flex-col items-start overflow-hidden text-left">
						<span className="text-sm font-semibold truncate w-32">
							{user.displayName || "User"}
						</span>
						<span className="text-[10px] text-sidebar-foreground/50 truncate w-32">
							{user.email}
						</span>
					</div>
					<MoreHorizontal className="ml-auto h-4 w-4 text-sidebar-foreground/40" />
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent
				className="w-56"
				align="start"
				side="right"
				sideOffset={10}
			>
				<DropdownMenuLabel className="font-normal">
					<div className="flex flex-col space-y-1">
						<p className="text-sm font-medium leading-none">
							{user.displayName}
						</p>
						<p className="text-xs leading-none text-muted-foreground">
							{user.email}
						</p>
					</div>
				</DropdownMenuLabel>
				<DropdownMenuSeparator />
				<DropdownMenuItem
					className="text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer gap-2"
					onClick={() => logout()}
				>
					<LogOut className="h-4 w-4" />
					Sign out
				</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}

function SidebarFooterContent() {
	const { meetDescription } = useConfig();
	const buildTime = process.env.NEXT_PUBLIC_BUILD_TIME;

	return (
		<div className="px-4 py-3 rounded-lg bg-sidebar-accent/50 space-y-2">
			{meetDescription && (
				<p className="text-xs text-sidebar-foreground/60 whitespace-pre-wrap">
					{meetDescription}
				</p>
			)}
			{buildTime && (
				<div
					className={cn(
						"text-[10px] text-sidebar-foreground/30 font-mono pt-2",
						meetDescription && "border-t border-sidebar-border/50",
					)}
				>
					Build: {new Date(buildTime).toLocaleString()}
				</div>
			)}
		</div>
	);
}
