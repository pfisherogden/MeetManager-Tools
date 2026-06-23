"use client";

import {
	AlertCircle,
	AlertTriangle,
	CheckCircle,
	Info,
	RefreshCw,
} from "lucide-react";
import { useState } from "react";
import { validateActiveMeet } from "@/app/actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";

interface Finding {
	severity: number; // 1: INFO, 2: WARNING, 3: CRITICAL
	category: string;
	message: string;
	affectedId: string;
}

export function MeetValidation() {
	const [loading, setLoading] = useState(false);
	const [results, setResults] = useState<{
		message: string;
		findings: Finding[];
	} | null>(null);
	const [filterSeverity, setFilterSeverity] = useState<number | null>(null); // null means Show All

	const runValidation = async () => {
		setLoading(true);
		try {
			const res = await validateActiveMeet();
			if (res.success) {
				setResults({ message: res.message, findings: res.findings });
			} else {
				setResults({
					message: res.message || "Failed to run validation.",
					findings: [],
				});
			}
		} catch (err: any) {
			setResults({
				message: err.message || "Failed to validate meet.",
				findings: [],
			});
		} finally {
			setLoading(false);
		}
	};

	const getSeverityBadge = (sev: number) => {
		switch (sev) {
			case 3: // CRITICAL
				return (
					<Badge
						variant="destructive"
						className="bg-red-500 hover:bg-red-600 gap-1 text-xs"
					>
						<AlertCircle className="h-3 w-3" /> Critical
					</Badge>
				);
			case 2: // WARNING
				return (
					<Badge className="bg-amber-500 hover:bg-amber-600 text-white gap-1 text-xs">
						<AlertTriangle className="h-3 w-3" /> Warning
					</Badge>
				);
			default:
				return (
					<Badge
						variant="secondary"
						className="bg-blue-100 text-blue-800 hover:bg-blue-200 gap-1 text-xs"
					>
						<Info className="h-3 w-3" /> Info
					</Badge>
				);
		}
	};

	const criticals = results?.findings.filter((f) => f.severity === 3) || [];
	const warnings = results?.findings.filter((f) => f.severity === 2) || [];
	const infos = results?.findings.filter((f) => f.severity === 1) || [];

	const filteredFindings =
		results?.findings.filter(
			(f) => filterSeverity === null || f.severity === filterSeverity,
		) || [];

	return (
		<Card className="border-border/50 shadow-md">
			<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
				<div>
					<CardTitle className="text-xl font-bold">
						Meet Rules & Data Validation
					</CardTitle>
					<CardDescription className="text-sm text-muted-foreground mt-1">
						Scan the active dataset for registry anomalies and TVSL league rule
						deviations.
					</CardDescription>
				</div>
				<Button
					onClick={runValidation}
					disabled={loading}
					className="gap-2 bg-blue-600 text-white hover:bg-blue-700"
				>
					<RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
					{loading ? "Scanning..." : "Run Validation Check"}
				</Button>
			</CardHeader>
			<CardContent>
				{!results && !loading && (
					<div className="text-center py-10 text-muted-foreground bg-muted/20 rounded-lg border border-dashed border-border/80">
						No validation data loaded. Click the button above to run checks on
						this meet.
					</div>
				)}

				{results && (
					<div className="space-y-6">
						{/* Status Summary Banner */}
						<div className="flex flex-col md:flex-row gap-4 p-4 rounded-lg bg-muted/30 border border-border/80 items-start md:items-center justify-between">
							<div className="space-y-1">
								<p className="font-semibold text-foreground text-sm">
									{results.message}
								</p>
								<div className="flex flex-wrap gap-4 mt-2 text-xs">
									<button
										type="button"
										onClick={() => setFilterSeverity(null)}
										className={`font-medium ${filterSeverity === null ? "underline text-foreground font-bold" : "text-muted-foreground"}`}
									>
										All ({results.findings.length})
									</button>
									<button
										type="button"
										onClick={() => setFilterSeverity(3)}
										className={`font-medium text-red-500 ${filterSeverity === 3 ? "underline font-bold" : "opacity-80"}`}
									>
										{criticals.length} Critical
									</button>
									<button
										type="button"
										onClick={() => setFilterSeverity(2)}
										className={`font-medium text-amber-600 ${filterSeverity === 2 ? "underline font-bold" : "opacity-80"}`}
									>
										{warnings.length} Warnings
									</button>
									<button
										type="button"
										onClick={() => setFilterSeverity(1)}
										className={`font-medium text-blue-600 ${filterSeverity === 1 ? "underline font-bold" : "opacity-80"}`}
									>
										{infos.length} Info
									</button>
								</div>
							</div>
							{results.findings.length === 0 && (
								<div className="flex items-center gap-2 text-emerald-600 self-end md:self-center">
									<CheckCircle className="h-6 w-6" />
									<span className="font-bold">Perfect Score</span>
								</div>
							)}
						</div>

						{/* Findings Lists */}
						{results.findings.length > 0 && (
							<div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
								{filteredFindings.length === 0 ? (
									<div className="text-center py-6 text-muted-foreground text-sm">
										No findings match the selected filter.
									</div>
								) : (
									filteredFindings.map((finding) => (
										<div
											key={`${finding.category}-${finding.affectedId || ""}-${finding.message}`}
											className="flex items-start justify-between p-3 rounded-lg border border-border bg-card hover:bg-muted/10 transition-colors"
										>
											<div className="space-y-1 pr-4">
												<div className="flex items-center gap-2">
													<span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
														{finding.category}
													</span>
													{finding.affectedId && (
														<span className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded text-foreground">
															ID: {finding.affectedId}
														</span>
													)}
												</div>
												<p className="text-sm text-foreground">
													{finding.message}
												</p>
											</div>
											<div className="shrink-0">
												{getSeverityBadge(finding.severity)}
											</div>
										</div>
									))
								)}
							</div>
						)}
					</div>
				)}
			</CardContent>
		</Card>
	);
}
