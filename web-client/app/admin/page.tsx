"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { updateAdminConfig } from "@/app/actions";
import { AppSidebar } from "@/components/app-sidebar";
import { useConfig } from "@/components/config-provider";
import { DatasetManager } from "@/components/dataset-manager";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function AdminPage() {
	const { meetName: initialMeetName, meetDescription: initialMeetDesc } =
		useConfig();

	const [meetName, setMeetName] = useState(initialMeetName);
	const [meetDescription, setMeetDescription] = useState(initialMeetDesc);
	const [loading, setLoading] = useState(false);

	// Sync state with context when context loads
	useEffect(() => {
		setMeetName(initialMeetName);
		setMeetDescription(initialMeetDesc);
	}, [initialMeetName, initialMeetDesc]);

	const handleSave = async (e: React.FormEvent) => {
		e.preventDefault();
		setLoading(true);
		try {
			await updateAdminConfig(meetName, meetDescription);
			toast.success("Configuration updated successfully");
			// Reload page to reflect changes in context if needed, or rely on wrapper re-render?
			// Context might not update immediately if we don't expose a setter.
			// For now, reload window is safest for global context update if we didn't implement sophisticated context update.
			// But revalidatePath on server might be enough for navigation, but not for client context.
			// Let's force reload for now.
			window.location.reload();
		} catch (err: any) {
			toast.error(`Failed to update configuration: ${err.message}`);
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="flex min-h-screen bg-background">
			<AppSidebar />
			<main className="flex-1 flex flex-col overflow-hidden">
				<div className="p-6 pb-0">
					<h1 className="text-2xl font-bold text-foreground">
						Admin Configuration
					</h1>
					<p className="text-muted-foreground">
						Manage global settings for the meet
					</p>
				</div>

				<div className="flex-1 p-6 space-y-6">
					<Card>
						<CardHeader>
							<CardTitle>Meet Details</CardTitle>
							<CardDescription>
								Configure the global display settings for the meet.
							</CardDescription>
						</CardHeader>
						<CardContent>
							<form onSubmit={handleSave} className="space-y-4">
								<div className="space-y-2">
									<Label htmlFor="meetName">Meet Name (Top Header)</Label>
									<Input
										id="meetName"
										value={meetName}
										onChange={(e) => setMeetName(e.target.value)}
										placeholder="e.g. Summer Season 2025"
									/>
								</div>

								<div className="space-y-2">
									<Label htmlFor="meetDesc">
										Meet Description (Sidebar Footer)
									</Label>
									<Textarea
										id="meetDesc"
										value={meetDescription}
										onChange={(e) => setMeetDescription(e.target.value)}
										placeholder="e.g. July 15-18, Miami FL"
										rows={3}
									/>
								</div>

								<Button type="submit" disabled={loading}>
									{loading ? "Saving..." : "Save Configuration"}
								</Button>
							</form>
						</CardContent>
					</Card>

					<DatasetManager />
				</div>
			</main>
		</div>
	);
}
