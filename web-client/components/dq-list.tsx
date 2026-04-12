"use client";

import { CheckCircle2, Info } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { getDisqualifications } from "@/app/actions";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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
	event: number;
	heat: number;
	lane: number;
	swimmer: string;
	infraction_code: string;
	createdAt: string;
}

export function DqList() {
	const [dqs, setDqs] = useState<DQRecord[]>([]);
	const [isLoading, setIsLoading] = useState(true);

	useEffect(() => {
		async function loadDqs() {
			try {
				const data = await getDisqualifications();
				setDqs(data);
			} catch (error) {
				console.error("Failed to load DQs:", error);
				toast.error("Failed to fetch disqualifications");
			} finally {
				setIsLoading(false);
			}
		}
		loadDqs();
	}, []);

	if (isLoading) {
		return (
			<div className="flex justify-center p-8">
				<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
			</div>
		);
	}

	return (
		<div className="p-6">
			<Card>
				<CardHeader>
					<div className="flex items-center justify-between">
						<h2 className="text-xl font-semibold">
							Submitted Disqualifications
						</h2>
						<Badge variant="secondary">{dqs.length} Total</Badge>
					</div>
				</CardHeader>
				<CardContent>
					{dqs.length === 0 ? (
						<div className="flex flex-col items-center justify-center p-12 text-muted-foreground border rounded-lg border-dashed">
							<Info className="h-12 w-12 mb-4 opacity-20" />
							<p>No disqualifications submitted yet</p>
						</div>
					) : (
						<Table>
							<TableHeader>
								<TableRow>
									<TableHead>Event</TableHead>
									<TableHead>Heat</TableHead>
									<TableHead>Lane</TableHead>
									<TableHead>Swimmer</TableHead>
									<TableHead>Infraction</TableHead>
									<TableHead>Submitted At</TableHead>
									<TableHead className="text-right">Status</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{dqs.map((dq) => (
									<TableRow key={dq.id}>
										<TableCell className="font-medium">#{dq.event}</TableCell>
										<TableCell>{dq.heat}</TableCell>
										<TableCell>
											<Badge variant="outline">{dq.lane}</Badge>
										</TableCell>
										<TableCell>{dq.swimmer}</TableCell>
										<TableCell>
											<code className="bg-muted px-1 py-0.5 rounded text-sm font-bold">
												{dq.infraction_code}
											</code>
										</TableCell>
										<TableCell className="text-sm text-muted-foreground">
											{new Date(dq.createdAt).toLocaleString()}
										</TableCell>
										<TableCell className="text-right">
											<div className="flex items-center justify-end gap-2 text-success">
												<CheckCircle2 className="h-4 w-4" />
												<span className="text-xs font-medium uppercase">
													Synced
												</span>
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
