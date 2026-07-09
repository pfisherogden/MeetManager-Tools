"use client";

import {
	AlertCircle,
	AlertTriangle,
	ArrowUpDown,
	CheckCircle,
	ChevronDown,
	ChevronUp,
	Filter,
	Info,
	RefreshCw,
	Search,
	X,
} from "lucide-react";
import { useMemo, useState } from "react";
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

type SortField = "severity" | "category" | "message" | "affectedId";
type SortDirection = "asc" | "desc";

export function MeetValidation() {
	const [loading, setLoading] = useState(false);
	const [results, setResults] = useState<{
		message: string;
		findings: Finding[];
	} | null>(null);

	// Filter state
	const [selectedSeverities, setSelectedSeverities] = useState<number[]>([
		1, 2, 3,
	]);
	const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
	const [searchQuery, setSearchQuery] = useState("");

	// Sort state
	const [sortField, setSortField] = useState<SortField | null>(null);
	const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

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

	// Group counts (all findings, unfiltered by current selections)
	const counts = useMemo(() => {
		if (!results)
			return {
				criticals: 0,
				warnings: 0,
				infos: 0,
				categories: {} as Record<string, number>,
			};
		const criticals = results.findings.filter((f) => f.severity === 3).length;
		const warnings = results.findings.filter((f) => f.severity === 2).length;
		const infos = results.findings.filter((f) => f.severity === 1).length;

		const categories = results.findings.reduce(
			(acc, f) => {
				acc[f.category] = (acc[f.category] || 0) + 1;
				return acc;
			},
			{} as Record<string, number>,
		);

		return { criticals, warnings, infos, categories };
	}, [results]);

	// Filter & Sort findings
	const processedFindings = useMemo(() => {
		if (!results) return [];

		let list = [...results.findings];

		// 1. Severity filter
		list = list.filter((f) => selectedSeverities.includes(f.severity));

		// 2. Category filter
		if (selectedCategories.length > 0) {
			list = list.filter((f) => selectedCategories.includes(f.category));
		}

		// 3. Search query filter
		if (searchQuery.trim() !== "") {
			const query = searchQuery.toLowerCase().trim();
			list = list.filter(
				(f) =>
					f.message.toLowerCase().includes(query) ||
					f.category.toLowerCase().includes(query) ||
					f.affectedId.toLowerCase().includes(query),
			);
		}

		// 4. Sort
		if (sortField) {
			list.sort((a, b) => {
				let valA = a[sortField];
				let valB = b[sortField];

				// Handle numeric conversion for affectedId if it is numeric
				if (sortField === "affectedId") {
					const numA = Number(valA);
					const numB = Number(valB);
					if (!Number.isNaN(numA) && !Number.isNaN(numB)) {
						valA = numA;
						valB = numB;
					}
				}

				if (valA < valB) return sortDirection === "asc" ? -1 : 1;
				if (valA > valB) return sortDirection === "asc" ? 1 : -1;
				return 0;
			});
		}

		return list;
	}, [
		results,
		selectedSeverities,
		selectedCategories,
		searchQuery,
		sortField,
		sortDirection,
	]);

	const toggleSeverity = (sev: number) => {
		setSelectedSeverities((prev) =>
			prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev],
		);
	};

	const toggleCategory = (cat: string) => {
		setSelectedCategories((prev) => (prev.includes(cat) ? [] : [cat]));
	};

	const handleSort = (field: SortField) => {
		if (sortField === field) {
			if (sortDirection === "asc") {
				setSortDirection("desc");
			} else {
				setSortField(null);
			}
		} else {
			setSortField(field);
			setSortDirection("asc");
		}
	};

	const renderSortIcon = (field: SortField) => {
		if (sortField !== field) {
			return (
				<ArrowUpDown className="ml-1 h-3.5 w-3.5 opacity-40 group-hover:opacity-75 transition-opacity" />
			);
		}
		return sortDirection === "asc" ? (
			<ChevronUp className="ml-1 h-3.5 w-3.5 text-blue-600 font-bold" />
		) : (
			<ChevronDown className="ml-1 h-3.5 w-3.5 text-blue-600 font-bold" />
		);
	};

	return (
		<Card className="border-border/50 shadow-md">
			<CardHeader className="flex flex-col md:flex-row items-start md:items-center justify-between space-y-4 md:space-y-0 pb-4">
				<div className="space-y-1">
					<CardTitle className="text-xl font-bold">
						Meet Rules & Data Validation
					</CardTitle>
					<CardDescription className="text-sm text-muted-foreground">
						Scan the active dataset for registry anomalies and TVSL league rule
						deviations.
					</CardDescription>
				</div>
				<Button
					onClick={runValidation}
					disabled={loading}
					className="w-full md:w-auto gap-2 bg-blue-600 text-white hover:bg-blue-700 font-semibold"
				>
					<RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
					{loading ? "Scanning..." : "Run Validation Check"}
				</Button>
			</CardHeader>

			<CardContent className="space-y-6">
				{!results && !loading && (
					<div className="text-center py-12 text-muted-foreground bg-muted/15 rounded-lg border border-dashed border-border/80">
						No validation data loaded. Click the button above to run checks on
						this meet.
					</div>
				)}

				{results && (
					<div className="space-y-6">
						{/* Summary Status Banner */}
						<div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/80 items-start md:items-center justify-between shadow-sm">
							<div className="space-y-1.5 w-full">
								<p className="font-semibold text-slate-800 text-sm">
									{results.message}
								</p>
								<div className="flex flex-wrap gap-4 text-xs font-medium mt-1">
									<span className="text-slate-600">
										Total Findings:{" "}
										<strong className="text-slate-900">
											{results.findings.length}
										</strong>
									</span>
									<span className="text-red-500 flex items-center gap-1">
										<span className="h-2 w-2 rounded-full bg-red-500" />
										Critical: <strong>{counts.criticals}</strong>
									</span>
									<span className="text-amber-600 flex items-center gap-1">
										<span className="h-2 w-2 rounded-full bg-amber-500" />
										Warnings: <strong>{counts.warnings}</strong>
									</span>
									<span className="text-blue-600 flex items-center gap-1">
										<span className="h-2 w-2 rounded-full bg-blue-400" />
										Info: <strong>{counts.infos}</strong>
									</span>
								</div>
							</div>
							{results.findings.length === 0 && (
								<div className="flex items-center gap-2 text-emerald-600 shrink-0">
									<CheckCircle className="h-6 w-6" />
									<span className="font-bold">Perfect Score</span>
								</div>
							)}
						</div>

						{/* Detailed Category Summary Chips */}
						{results.findings.length > 0 && (
							<div className="space-y-2">
								<h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
									Categories Summary (Click to Filter)
								</h3>
								<div className="flex flex-wrap gap-1.5">
									<button
										type="button"
										onClick={() => setSelectedCategories([])}
										className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-all ${
											selectedCategories.length === 0
												? "bg-slate-800 text-white shadow-sm"
												: "bg-slate-100 text-slate-600 hover:bg-slate-200"
										}`}
									>
										All Categories
									</button>
									{Object.entries(counts.categories).map(([cat, count]) => {
										const active = selectedCategories.includes(cat);
										return (
											<button
												key={cat}
												type="button"
												onClick={() => toggleCategory(cat)}
												className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-all flex items-center gap-1.5 ${
													active
														? "bg-blue-600 text-white shadow-sm"
														: "bg-slate-100 text-slate-600 hover:bg-slate-200"
												}`}
											>
												{cat}
												<span
													className={`px-1.5 py-0.2 rounded-full text-[10px] ${
														active
															? "bg-blue-800 text-white"
															: "bg-slate-200 text-slate-700"
													}`}
												>
													{count}
												</span>
											</button>
										);
									})}
								</div>
							</div>
						)}

						{/* Filter Panel & Search */}
						{results.findings.length > 0 && (
							<div className="flex flex-col lg:flex-row gap-4 p-4 rounded-xl border border-slate-200 bg-slate-50/50 shadow-sm">
								{/* Checkbox Severities */}
								<div className="flex flex-wrap items-center gap-4 shrink-0 lg:border-r lg:border-slate-200 lg:pr-4">
									<span className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
										<Filter className="h-3.5 w-3.5" /> Severities
									</span>
									<label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
										<input
											type="checkbox"
											checked={selectedSeverities.includes(3)}
											onChange={() => toggleSeverity(3)}
											className="rounded border-slate-300 text-red-500 focus:ring-red-500 h-4 w-4"
										/>
										<span className="text-red-500">
											Critical ({counts.criticals})
										</span>
									</label>
									<label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
										<input
											type="checkbox"
											checked={selectedSeverities.includes(2)}
											onChange={() => toggleSeverity(2)}
											className="rounded border-slate-300 text-amber-500 focus:ring-amber-500 h-4 w-4"
										/>
										<span className="text-amber-600">
											Warning ({counts.warnings})
										</span>
									</label>
									<label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
										<input
											type="checkbox"
											checked={selectedSeverities.includes(1)}
											onChange={() => toggleSeverity(1)}
											className="rounded border-slate-300 text-blue-500 focus:ring-blue-500 h-4 w-4"
										/>
										<span className="text-blue-600">Info ({counts.infos})</span>
									</label>
								</div>

								{/* Search Bar */}
								<div className="relative flex-1">
									<Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground opacity-70" />
									<input
										type="text"
										placeholder="Search by swimmer, ID, description..."
										value={searchQuery}
										onChange={(e) => setSearchQuery(e.target.value)}
										className="pl-9 pr-8 py-2 w-full text-sm rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
									/>
									{searchQuery && (
										<button
											type="button"
											onClick={() => setSearchQuery("")}
											className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
										>
											<X className="h-4 w-4" />
										</button>
									)}
								</div>
							</div>
						)}

						{/* Findings List (Table Headers + Scrollable Panel) */}
						{results.findings.length > 0 && (
							<div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-white">
								{/* Sortable Header Row */}
								<div className="grid grid-cols-[110px_140px_100px_1fr] gap-4 bg-slate-50 border-b border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-600 uppercase tracking-wider select-none">
									<button
										type="button"
										onClick={() => handleSort("severity")}
										className="flex items-center text-left hover:text-slate-900 group transition-colors"
									>
										Severity {renderSortIcon("severity")}
									</button>
									<button
										type="button"
										onClick={() => handleSort("category")}
										className="flex items-center text-left hover:text-slate-900 group transition-colors"
									>
										Category {renderSortIcon("category")}
									</button>
									<button
										type="button"
										onClick={() => handleSort("affectedId")}
										className="flex items-center text-left hover:text-slate-900 group transition-colors"
									>
										Swimmer ID {renderSortIcon("affectedId")}
									</button>
									<button
										type="button"
										onClick={() => handleSort("message")}
										className="flex items-center text-left hover:text-slate-900 group transition-colors"
									>
										Finding Details {renderSortIcon("message")}
									</button>
								</div>

								{/* Findings Rows Panel */}
								<div className="divide-y divide-slate-100 max-h-[450px] overflow-y-auto pr-0.5">
									{processedFindings.length === 0 ? (
										<div className="text-center py-10 text-muted-foreground text-sm">
											No validation findings match your current filters.
										</div>
									) : (
										processedFindings.map((finding) => (
											<div
												key={`${finding.category}-${finding.affectedId || ""}-${finding.message}`}
												className="grid grid-cols-[110px_140px_100px_1fr] gap-4 items-start px-4 py-3 hover:bg-slate-50/50 transition-colors text-sm"
											>
												<div className="shrink-0 pt-0.5">
													{getSeverityBadge(finding.severity)}
												</div>
												<div className="font-semibold text-slate-700 tracking-wide text-xs uppercase pt-1">
													{finding.category}
												</div>
												<div className="font-mono text-xs bg-slate-100/80 border border-slate-200/50 text-slate-600 px-2 py-0.5 rounded text-center w-fit">
													{finding.affectedId
														? `ID: ${finding.affectedId}`
														: "—"}
												</div>
												<div className="text-slate-700 pr-2 leading-relaxed">
													{finding.message}
												</div>
											</div>
										))
									)}
								</div>
							</div>
						)}
					</div>
				)}
			</CardContent>
		</Card>
	);
}
