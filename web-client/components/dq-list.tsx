"use client";

import { CheckCircle2, Info, Loader2, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { clearAllDqs, deleteDq, getDisqualifications } from "@/app/actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";

interface DQRecord {
	id: string;
	client_id?: string;
	event: number;
	heat: number;
	lane: number;
	swimmer: string;
	infraction_code: string;
	notes?: string;
	createdAt: string;
}

export function DqList() {
	const [dqs, setDqs] = useState<DQRecord[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [isDeleting, setIsDeleting] = useState<string | null>(null);
	const [isClearing, setIsClearing] = useState(false);

	const loadDqs = useCallback(async () => {
		setIsLoading(true);
		try {
			const data = await getDisqualifications();
			setDqs(data.disqualifications || []);
		} catch (error) {
			console.error("Failed to load DQs:", error);
			toast.error("Failed to fetch disqualifications");
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		loadDqs();
	}, [loadDqs]);

	const handleDelete = async (id: string) => {
		if (!confirm("Are you sure you want to delete this DQ?")) return;
		setIsDeleting(id);
		try {
			const res = await deleteDq(id);
			if (res.success) {
				toast.success("DQ deleted");
				setDqs(dqs.filter((dq) => dq.id !== id));
			} else {
				toast.error(res.message || "Delete failed");
			}
		} catch (_error) {
			toast.error("An error occurred");
		} finally {
			setIsDeleting(null);
		}
	};

	const handleClearAll = async () => {
		if (
			!confirm(
				"Are you sure you want to delete ALL submitted DQs? This cannot be undone.",
			)
		)
			return;
		setIsClearing(true);
		try {
			const res = await clearAllDqs();
			if (res.success) {
				toast.success("All DQs cleared");
				setDqs([]);
			} else {
				toast.error(res.message || "Clear failed");
			}
		} catch (_error) {
			toast.error("An error occurred");
		} finally {
			setIsClearing(false);
		}
	};

	if (isLoading && dqs.length === 0) {
		return (
			<div className="flex justify-center p-12">
				<Loader2 className="animate-spin h-8 w-8 text-primary" />
			</div>
		);
	}

	return (
		<div className="p-6 space-y-4">
			<div className="flex items-center justify-between">
				<div>
					<h2 className="text-2xl font-bold tracking-tight">DQ Management</h2>
					<p className="text-muted-foreground">
						Review and manage disqualifications submitted by judges.
					</p>
				</div>
				<div className="flex items-center gap-2">
					<Button
						variant="outline"
						size="sm"
						onClick={loadDqs}
						disabled={isLoading}
					>
						<RefreshCw
							className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`}
						/>
						Refresh
					</Button>
					{dqs.length > 0 && (
						<Button
							variant="destructive"
							size="sm"
							onClick={handleClearAll}
							disabled={isClearing}
						>
							{isClearing ? (
								<Loader2 className="h-4 w-4 mr-2 animate-spin" />
							) : (
								<Trash2 className="h-4 w-4 mr-2" />
							)}
							Clear All
						</Button>
					)}
				</div>
			</div>

			<Card>
				<CardHeader className="pb-3">
					<div className="flex items-center justify-between">
						<CardTitle className="text-lg font-medium">
							Recent Submissions
						</CardTitle>
						<Badge variant="secondary">{dqs.length} Total</Badge>
					</div>
				</CardHeader>
				<CardContent>
					{dqs.length === 0 ? (
						<div className="flex flex-col items-center justify-center p-12 text-muted-foreground border rounded-lg border-dashed">
							<Info className="h-12 w-12 mb-4 opacity-20" />
							<p>No disqualifications found</p>
							<Button variant="link" onClick={loadDqs} className="mt-2">
								Check again
							</Button>
						</div>
					) : (
						<Table>
							<TableHeader>
								<TableRow>
									<TableHead>Event</TableHead>
									<TableHead>H/L</TableHead>
									<TableHead>Swimmer/Team</TableHead>
									<TableHead>Judge</TableHead>
									<TableHead>Infraction</TableHead>
									<TableHead>Notes</TableHead>
									<TableHead>Submitted At</TableHead>
									<TableHead className="text-right">Actions</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{dqs.map((dq) => (
									<TableRow key={dq.id}>
										<TableCell className="font-medium">#{dq.event}</TableCell>
										<TableCell>
											{dq.heat}/{dq.lane}
										</TableCell>
										<TableCell className="max-w-[180px] truncate">
											{dq.swimmer}
										</TableCell>
										<TableCell className="font-medium text-blue-600">
											{dq.client_id || "Unknown"}
										</TableCell>
										<TableCell>
											<code className="bg-muted px-1.5 py-0.5 rounded text-xs font-bold border border-primary/10">
												{dq.infraction_code}
											</code>
										</TableCell>
										<TableCell className="max-w-[200px] truncate italic text-sm text-muted-foreground">
											{dq.notes || "-"}
										</TableCell>
										<TableCell className="text-xs text-muted-foreground">
											{new Date(dq.createdAt).toLocaleString(undefined, {
												month: "short",
												day: "numeric",
												hour: "2-digit",
												minute: "2-digit",
											})}
										</TableCell>
										<TableCell className="text-right">
											<div className="flex items-center justify-end gap-2">
												<div className="flex items-center gap-1.5 text-success mr-2">
													<CheckCircle2 className="h-3.5 w-3.5" />
													<span className="text-[10px] font-bold uppercase">
														Synced
													</span>
												</div>
												<Button
													variant="ghost"
													size="icon"
													className="h-8 w-8 text-muted-foreground hover:text-destructive"
													onClick={() => handleDelete(dq.id)}
													disabled={isDeleting === dq.id}
												>
													{isDeleting === dq.id ? (
														<Loader2 className="h-4 w-4 animate-spin" />
													) : (
														<Trash2 className="h-4 w-4" />
													)}
												</Button>
											</div>
										</TableCell>
									</TableRow>
								))}
							</TableBody>
						</Table>
					)}
				</CardContent>
			</Card>
		</div>
	);
}
