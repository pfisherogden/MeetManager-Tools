"use client";

import {
	Check,
	ChevronsUpDown,
	Download,
	FileText,
	Filter,
	Loader2,
	Package,
	Plus,
	Settings2,
	Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
	generateReport,
	generateReportBundle,
	getJobStatus,
	getTeams,
} from "@/app/actions";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import {
	Command,
	CommandEmpty,
	CommandGroup,
	CommandInput,
	CommandItem,
	CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { RendererType } from "@/lib/proto/meetmanager/v1/meet_manager";
import { cn } from "@/lib/utils";

const reportTypes = [
	{
		id: 0,
		name: "Psych Sheet",
		description: "List of entries by event with seed times.",
	},
	{
		id: 1,
		name: "Meet Entries",
		description: "Individual and relay entries grouped by team.",
	},
	{
		id: 2,
		name: "Lineup Sheets",
		description: "Heat and lane assignments for parent volunteers.",
	},
	{
		id: 3,
		name: "Meet Results",
		description: "Final times, places, and points by event.",
	},
	{
		id: 4,
		name: "Meet Program (PDF)",
		description: "Traditional 2-column program with heat/lane assignments.",
	},
	{
		id: 5,
		name: "Meet Program (HTML)",
		description: "Interactive HTML view of the 2-column meet program.",
	},
	{
		id: 6,
		name: "Entries (HY-TEK Style)",
		description: "Traditional 2-column entries report with relay legs.",
	},
	{
		id: 7,
		name: "Entries (Club Style)",
		description: "Single-column format optimized for team distribution.",
	},
	{
		id: 8,
		name: "Lane Timer Sheets",
		description: "Printable scoring sheets for lane timers.",
	},
	{
		id: 9,
		name: "Judge Sheets",
		description: "Official sheets for S&T judges with DQ lines.",
	},
	{
		id: 10,
		name: "CTS Scoreboard Export",
		description: "Scoreboard start lists (.scb) and Dolphin events (.csv).",
	},
	{
		id: 11,
		name: "Swimmer Check-in Sheet",
		description: "Excel spreadsheet for swimmer check-in and scratch tracking.",
	},
];

interface CustomPackItem {
	id: string;
	type: number;
	title: string;
	teamFilter: string;
	genderFilter: string;
	ageGroupFilter: string;
	zebraStriping: boolean;
	includeBlankLanes?: boolean;
	breakEverySixEvents?: boolean;
}

interface ReportsManagerProps {
	initialTeams?: { id: string; name: string }[];
}

export function ReportsManager({
	initialTeams: propTeams = [],
}: ReportsManagerProps) {
	const [selectedType, setSelectedType] = useState<number | null>(null);
	const [title, setTitle] = useState("");
	const [teamFilter, setTeamFilter] = useState("");
	const [genderFilter, setGenderFilter] = useState("Mixed");
	const [ageGroupFilter, setAgeGroupFilter] = useState("Open");
	const [zebraStriping, setZebraStriping] = useState(false);
	const [includeBlankLanes, setIncludeBlankLanes] = useState(true);
	const [breakEverySixEvents, setBreakEverySixEvents] = useState(true);
	const [rendererType, setRendererType] = useState<RendererType>(
		RendererType.RENDERER_TYPE_UNSPECIFIED,
	);
	const [isGenerating, setIsGenerating] = useState(false);
	const [htmlPreviewMode, setHtmlPreviewMode] = useState(false);

	// Custom Pack State
	const [customPack, setCustomPack] = useState<CustomPackItem[]>([]);
	const [isBundling, setIsBundling] = useState(false);
	const [_jobId, setJobId] = useState<string | null>(null);
	const [jobProgress, setJobProgress] = useState(0);
	const [jobMessage, setJobMessage] = useState("");

	const pollingInterval = useRef<NodeJS.Timeout | null>(null);
	const downloadTriggered = useRef<string | null>(null);

	// Improved Team Filter State
	const [initialTeams, setTeams] =
		useState<{ id: string; name: string }[]>(propTeams);
	const [teamFilterOpen, setTeamFilterOpen] = useState(false);
	const [presetTeamOpen, setPresetTeamOpen] = useState(false);
	const [presetTeamFilter, setPresetTeamFilter] = useState("All Teams");

	useEffect(() => {
		if (propTeams.length > 0) {
			setTeams(propTeams);
		} else {
			getTeams().then((res) => {
				if (res.teams) {
					setTeams(res.teams.map((t) => ({ id: String(t.id), name: t.name })));
				}
			});
		}
	}, [propTeams]);

	const updatePackItem = (id: string, updates: Partial<CustomPackItem>) => {
		setCustomPack(
			customPack.map((item) =>
				item.id === id ? { ...item, ...updates } : item,
			),
		);
	};

	const startPolling = (jobId: string, _filename: string) => {
		setJobId(jobId);
		setJobProgress(0);
		setJobMessage("Starting...");
		setIsBundling(true);

		if (pollingInterval.current) clearInterval(pollingInterval.current);

		pollingInterval.current = setInterval(async () => {
			try {
				const status = await getJobStatus(jobId);
				if (status.status === 3) {
					// COMPLETED
					setJobProgress(100);
					setJobMessage("Complete");
					if (pollingInterval.current) clearInterval(pollingInterval.current);
					setIsBundling(false);

					// Trigger download if not already done
					if (downloadTriggered.current !== jobId && status.bundleUrl) {
						downloadTriggered.current = jobId;
						window.location.href = status.bundleUrl;

						// Also open any google sheets
						if (status.googleSheetUrls && status.googleSheetUrls.length > 0) {
							for (const url of status.googleSheetUrls) {
								window.open(url, "_blank");
							}
						}

						toast.success(
							status.googleSheetUrls && status.googleSheetUrls.length > 0
								? "Pack generated! Check-in sheets opened in new tabs."
								: "Custom pack generated successfully",
						);
					}
				} else if (status.status === 4) {
					// FAILED
					setJobMessage(`Error: ${status.message || "Unknown error"}`);
					if (pollingInterval.current) clearInterval(pollingInterval.current);
					setIsBundling(false);
					toast.error("Generation failed");
				} else {
					setJobProgress(status.progress * 100);
					setJobMessage(status.message || "Processing...");
				}
			} catch (error) {
				console.error("Polling error:", error);
			}
		}, 2000);
	};

	const handleGenerate = async () => {
		if (selectedType === null) return;
		setIsGenerating(true);

		const reportTitle =
			title || reportTypes.find((r) => r.id === selectedType)?.name || "Report";

		try {
			const result = await generateReport({
				type: selectedType,
				title: reportTitle,
				teamFilter: teamFilter,
				genderFilter: genderFilter,
				ageGroupFilter: ageGroupFilter,
				columnsOnPage: 2,
				showRelaySwimmers: true,
				zebraStriping: zebraStriping,
				rendererType: rendererType,
				htmlPreview: htmlPreviewMode,
				includeBlankLanes: selectedType === 8 ? includeBlankLanes : undefined,
				breakEverySixEvents:
					selectedType === 8 ? breakEverySixEvents : undefined,
			});

			if (result.success) {
				// 1. Handle Google Sheet
				if (result.googleSheetUrl) {
					window.open(result.googleSheetUrl, "_blank");
				}

				// 2. Handle HTML Preview
				if ((selectedType === 5 || htmlPreviewMode) && result.htmlContent) {
					const win = window.open("", "_blank");
					if (win) {
						win.document.write(result.htmlContent);
						win.document.close();
					}
				} else if (result.pdfContentBase64) {
					const link = document.createElement("a");
					link.href = `data:application/pdf;base64,${result.pdfContentBase64}`;
					link.download = result.filename || `${reportTitle}.pdf`;
					link.click();
				}
				toast.success("Report generated successfully");
			} else {
				toast.error(result.message || "Failed to generate report");
			}
		} catch (_error: unknown) {
			toast.error("An error occurred during report generation");
		} finally {
			setIsGenerating(false);
		}
	};

	const addToPack = () => {
		if (selectedType === null) return;

		const typeInfo = reportTypes.find((r) => r.id === selectedType);
		const newItem: CustomPackItem = {
			id: crypto.randomUUID(),
			type: selectedType,
			title: title || typeInfo?.name || "Report",
			teamFilter: teamFilter || "All Teams",
			genderFilter: genderFilter,
			ageGroupFilter: ageGroupFilter,
			zebraStriping: zebraStriping,
			includeBlankLanes: selectedType === 8 ? includeBlankLanes : undefined,
			breakEverySixEvents: selectedType === 8 ? breakEverySixEvents : undefined,
		};
		setCustomPack([...customPack, newItem]);
		toast.success("Added to custom pack");
	};

	const removeFromPack = (id: string) => {
		setCustomPack(customPack.filter((item) => item.id !== id));
		toast.success("Removed from pack");
	};

	const clearPack = () => {
		setCustomPack([]);
		toast.success("Pack cleared");
	};

	const handleGenerateBundle = async () => {
		if (customPack.length === 0) return;
		setIsBundling(true);
		setJobProgress(0);
		setJobMessage("Initializing bundle...");

		try {
			// Convert pack items to requests
			const requests = customPack.map((item) => ({
				type: item.type,
				title: item.title,
				teamFilter: item.teamFilter === "All Teams" ? "" : item.teamFilter,
				genderFilter: item.genderFilter,
				ageGroupFilter: item.ageGroupFilter,
				columnsOnPage: 2,
				showRelaySwimmers: true,
				zebraStriping: item.zebraStriping,
				rendererType: rendererType,
				htmlPreview: false,
				includeBlankLanes: item.includeBlankLanes,
				breakEverySixEvents: item.breakEverySixEvents,
			}));

			const timestamp = new Date()
				.toISOString()
				.replace(/[:.]/g, "-")
				.slice(0, 19);
			const bundleName = `meet_reports_${timestamp}.zip`;

			const frontendUrl =
				typeof window !== "undefined" ? window.location.origin : undefined;
			const result = await generateReportBundle(
				requests,
				bundleName,
				frontendUrl,
			);

			if (result.success && result.jobId) {
				startPolling(result.jobId, bundleName);
			} else {
				toast.error(result.message || "Failed to start bundle generation");
				setIsBundling(false);
			}
		} catch (_error: unknown) {
			toast.error("An error occurred during bundle generation");
			setIsBundling(false);
		}
	};

	const applyPreset = (preset: (typeof reportPresets)[0]) => {
		const newItems: CustomPackItem[] = preset.reports.map((r: any) => ({
			id: crypto.randomUUID(),
			type: r.type,
			title: r.title,
			teamFilter:
				r.teamFilter !== undefined
					? r.teamFilter
					: presetTeamFilter === "All Teams"
						? ""
						: presetTeamFilter,
			genderFilter: r.genderFilter || "Mixed",
			ageGroupFilter: r.ageGroupFilter || "Open",
			zebraStriping: r.zebraStriping || false,
		}));
		setCustomPack([...customPack, ...newItems]);
		toast.success(`Applied ${preset.name} to builder`);

		// Scroll builder into view
		const builder = document.getElementById("report-builder");
		builder?.scrollIntoView({ behavior: "smooth" });
	};

	const reportPresets = [
		{
			id: "default",
			name: "Default Meet Pack",
			description: "Operational reports for meet day (Summer 2025 standard)",
			reports: [
				{
					type: 1,
					title: "Parent Entry List - DP Only",
				},
				{
					type: 8,
					title: "Lane Timer Sheets",
					teamFilter: "",
				},
				// Lineup Reports (Girls)
				{
					type: 4,
					title: "Lineup: Girls 6&U",
					genderFilter: "Girls",
					ageGroupFilter: "6 & under",
				},
				{
					type: 4,
					title: "Lineup: Girls 7-8",
					genderFilter: "Girls",
					ageGroupFilter: "7-8",
				},
				{
					type: 4,
					title: "Lineup: Girls 9-10",
					genderFilter: "Girls",
					ageGroupFilter: "9-10",
				},
				// Lineup Reports (Boys+Mixed)
				{
					type: 4,
					title: "Lineup: Boys 6&U",
					genderFilter: "Boys",
					ageGroupFilter: "6 & under",
				},
				{
					type: 4,
					title: "Lineup: Boys 7-8",
					genderFilter: "Boys",
					ageGroupFilter: "7-8",
				},
				{
					type: 4,
					title: "Lineup: Boys 9-10",
					genderFilter: "Boys",
					ageGroupFilter: "9-10",
				},
				// Posting Programs
				{ type: 4, title: "Posting: Girls only", genderFilter: "Girls" },
				{ type: 4, title: "Posting: Boys+Mixed", genderFilter: "Boys" },
				// Operational
				{ type: 9, title: "Stroke & Turn Program", teamFilter: "" },
				{ type: 4, title: "Computer Team Program", teamFilter: "" },
				{ type: 4, title: "Complete Meet Program", teamFilter: "" },
				{ type: 10, title: "CTS Scoreboard Export", teamFilter: "" },
				{ type: 11, title: "Swimmer Check-in Sheet" },
			],
		},
		{
			id: "test",
			name: "Test Bundle (Fast)",
			description: "Small bundle for E2E verification",
			reports: [
				{ type: 8, title: "Timer Sheets", teamFilter: "" },
				{ type: 4, title: "Program", teamFilter: "" },
			],
		},
		{
			id: "lineups",
			name: "Lineup Sheets",
			description: "Volunteer sheets for all teams",
			reports: [{ type: 2, title: "Team Lineup Sheets" }],
		},
		{
			id: "results",
			name: "Full Results",
			description: "Complete meet results including scores",
			reports: [
				{ type: 3, title: "Official Meet Results" },
				{ type: 3, title: "Team Scores", zebraStriping: true },
			],
		},
	];

	const genderOptions = ["Mixed", "Girls", "Boys"];
	const ageGroupOptions = [
		"Open",
		"6 & under",
		"7-8",
		"9-10",
		"11-12",
		"13-14",
		"15-18",
	];

	return (
		<div className="p-6 space-y-8 max-w-6xl mx-auto">
			<div className="grid grid-cols-1 2xl:grid-cols-3 gap-8">
				<div className="2xl:col-span-2 space-y-6">
					<Card className="shadow-lg border-primary/10">
						<CardHeader className="bg-primary/5">
							<div className="flex items-center gap-2">
								<FileText className="h-5 w-5 text-primary" />
								<CardTitle>Available Reports</CardTitle>
							</div>
							<CardDescription>
								Select a report type to configure and generate.
							</CardDescription>
						</CardHeader>
						<CardContent className="p-0">
							<div className="grid grid-cols-1 md:grid-cols-2 divide-x divide-y">
								{reportTypes.map((report) => (
									<button
										key={report.id}
										type="button"
										onClick={() => {
											setSelectedType(report.id);
											setTitle(report.name);
										}}
										className={cn(
											"flex flex-col items-start p-6 text-left transition-all hover:bg-muted/50 group",
											selectedType === report.id &&
												"bg-primary/5 ring-2 ring-primary/20 ring-inset",
										)}
										data-testid={`report-card-${report.name.toLowerCase().replace(/\s+/g, "-")}`}
									>
										<div className="flex items-center gap-3 mb-2">
											<div
												className={cn(
													"w-10 h-10 rounded-xl flex items-center justify-center transition-colors",
													selectedType === report.id
														? "bg-primary text-white"
														: "bg-primary/10 text-primary group-hover:bg-primary/20",
												)}
											>
												<FileText className="h-5 w-5" />
											</div>
											<h3 className="font-bold text-lg">{report.name}</h3>
										</div>
										<p className="text-sm text-muted-foreground leading-relaxed">
											{report.description}
										</p>
									</button>
								))}
							</div>
						</CardContent>
					</Card>

					<Card className="shadow-lg border-primary/10">
						<CardHeader className="bg-primary/5 border-b">
							<div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
								<div className="flex items-center gap-2">
									<Package className="h-5 w-5 text-primary" />
									<CardTitle>Report Presets</CardTitle>
								</div>
								<div className="flex items-center gap-2">
									<Popover
										open={presetTeamOpen}
										onOpenChange={setPresetTeamOpen}
									>
										<PopoverTrigger asChild>
											<Button
												variant="outline"
												size="sm"
												data-testid="preset-team-filter-trigger"
												className="h-8 min-w-[120px] justify-between"
											>
												{presetTeamFilter}
												<ChevronsUpDown className="ml-2 h-3 w-3 opacity-50" />
											</Button>
										</PopoverTrigger>
										<PopoverContent className="w-[200px] p-0">
											<Command>
												<CommandInput placeholder="Search teams..." />
												<CommandList>
													<CommandEmpty>No team found.</CommandEmpty>
													<CommandGroup>
														<CommandItem
															onSelect={() => {
																setPresetTeamFilter("All Teams");
																setPresetTeamOpen(false);
															}}
														>
															<Check
																className={cn(
																	"mr-2 h-4 w-4",
																	presetTeamFilter === "All Teams"
																		? "opacity-100"
																		: "opacity-0",
																)}
															/>
															All Teams
														</CommandItem>
														{initialTeams.map((team) => (
															<CommandItem
																key={team.id}
																onSelect={() => {
																	setPresetTeamFilter(team.name);
																	setPresetTeamOpen(false);
																}}
															>
																<Check
																	className={cn(
																		"mr-2 h-4 w-4",
																		presetTeamFilter === team.name
																			? "opacity-100"
																			: "opacity-0",
																	)}
																/>
																{team.name}
															</CommandItem>
														))}
													</CommandGroup>
												</CommandList>
											</Command>
										</PopoverContent>
									</Popover>
								</div>
							</div>
							<CardDescription>
								Commonly used combinations of reports for specific meet roles.
							</CardDescription>
						</CardHeader>
						<CardContent className="grid grid-cols-1 xl:grid-cols-2 gap-4 p-6">
							{reportPresets.map((preset) => (
								<div
									key={preset.id}
									className="flex flex-col justify-between p-4 rounded-lg border bg-card hover:bg-accent/5 transition-colors gap-4"
								>
									<div className="space-y-1">
										<h4 className="font-bold text-sm">{preset.name}</h4>
										<p className="text-xs text-muted-foreground line-clamp-2">
											{preset.description}
										</p>
										<div className="flex flex-wrap gap-1.5 mt-2">
											{preset.reports.slice(0, 4).map((r, _i) => (
												<span
													key={`${r.type}-${r.title.replace(/\s+/g, "-")}`}
													className="px-2 py-0.5 bg-muted rounded text-[9px] font-medium"
												>
													{r.title}
												</span>
											))}
											{preset.reports.length > 4 && (
												<span className="text-[9px] text-muted-foreground font-medium px-1">
													+{preset.reports.length - 4} more
												</span>
											)}
										</div>
									</div>
									<Button
										size="sm"
										variant="secondary"
										onClick={() => applyPreset(preset)}
										data-testid={`preset-apply-${preset.id}`}
										className="w-full shrink-0 mt-auto"
									>
										Apply to Builder
									</Button>
								</div>
							))}
						</CardContent>
					</Card>
				</div>

				<div className="space-y-6">
					{selectedType !== null && (
						<Card
							data-testid="report-configuration-card"
							data-report-status={
								isGenerating ? "generating" : isBundling ? "bundling" : "idle"
							}
							data-job-progress={jobProgress}
							data-job-message={jobMessage}
							className="shadow-lg"
						>
							<CardHeader>
								<div className="flex items-center gap-2">
									<Settings2 className="h-5 w-5 text-primary" />
									<CardTitle>Configure Report</CardTitle>
								</div>
								<CardDescription>
									Customize the{" "}
									{reportTypes.find((r) => r.id === selectedType)?.name} before
									generating.
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-6">
								<div className="space-y-2">
									<Label htmlFor="title">Custom Report Title</Label>
									<Input
										id="title"
										placeholder={
											reportTypes.find((r) => r.id === selectedType)?.name ||
											"Report Title"
										}
										value={title}
										onChange={(e) => setTitle(e.target.value)}
									/>
								</div>

								<div className="space-y-2">
									<Label>Team Filter</Label>
									<Popover
										open={teamFilterOpen}
										onOpenChange={setTeamFilterOpen}
									>
										<PopoverTrigger asChild>
											<Button
												variant="outline"
												className="w-full justify-between"
												role="combobox"
												data-testid="team-filter-trigger"
											>
												{teamFilter || "All Teams"}
												<ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
											</Button>
										</PopoverTrigger>
										<PopoverContent className="w-full p-0">
											<Command>
												<CommandInput placeholder="Filter by team..." />
												<CommandList>
													<CommandEmpty>No team found.</CommandEmpty>
													<CommandGroup>
														<CommandItem
															onSelect={() => {
																setTeamFilter("");
																setTeamFilterOpen(false);
															}}
														>
															<Check
																className={cn(
																	"mr-2 h-4 w-4",
																	teamFilter === ""
																		? "opacity-100"
																		: "opacity-0",
																)}
															/>
															All Teams
														</CommandItem>
														{initialTeams.map((team) => (
															<CommandItem
																key={team.id}
																onSelect={() => {
																	setTeamFilter(team.name);
																	setTeamFilterOpen(false);
																}}
															>
																<Check
																	className={cn(
																		"mr-2 h-4 w-4",
																		teamFilter === team.name
																			? "opacity-100"
																			: "opacity-0",
																	)}
																/>
																{team.name}
															</CommandItem>
														))}
													</CommandGroup>
												</CommandList>
											</Command>
										</PopoverContent>
									</Popover>
								</div>

								<div className="grid grid-cols-2 gap-4">
									<div className="space-y-2">
										<Label>Gender</Label>
										<Select
											value={genderFilter}
											onValueChange={setGenderFilter}
										>
											<SelectTrigger>
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												{genderOptions.map((opt) => (
													<SelectItem key={opt} value={opt}>
														{opt}
													</SelectItem>
												))}
											</SelectContent>
										</Select>
									</div>
									<div className="space-y-2">
										<Label>Age Group</Label>
										<Select
											value={ageGroupFilter}
											onValueChange={setAgeGroupFilter}
										>
											<SelectTrigger>
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												{ageGroupOptions.map((opt) => (
													<SelectItem key={opt} value={opt}>
														{opt}
													</SelectItem>
												))}
											</SelectContent>
										</Select>
									</div>
								</div>

								<div className="grid grid-cols-2 gap-4">
									<div className="space-y-2">
										<Label>Zebra Striping</Label>
										<div className="flex items-center gap-2 h-10 px-3 rounded-md border bg-muted/30">
											<Switch
												checked={zebraStriping}
												onCheckedChange={setZebraStriping}
											/>
											<span className="text-xs">
												{zebraStriping ? "Enabled" : "Disabled"}
											</span>
										</div>
									</div>
									<div className="space-y-2">
										<Label>Rendering Engine</Label>
										<Select
											value={
												rendererType === RendererType.RENDERER_TYPE_UNSPECIFIED
													? RendererType.RENDERER_TYPE_PLAYWRIGHT.toString()
													: rendererType.toString()
											}
											onValueChange={(v) =>
												setRendererType(Number.parseInt(v, 10) as RendererType)
											}
										>
											<SelectTrigger
												className="w-full"
												data-testid="rendering-engine-selector"
											>
												<SelectValue placeholder="Select rendering engine" />
											</SelectTrigger>
											<SelectContent>
												<SelectItem
													value={RendererType.RENDERER_TYPE_PLAYWRIGHT.toString()}
												>
													Playwright (Fast, Chromium-based)
												</SelectItem>
												<SelectItem
													value={RendererType.RENDERER_TYPE_WEASYPRINT.toString()}
												>
													WeasyPrint (Standard, Python-based)
												</SelectItem>
											</SelectContent>
										</Select>
									</div>
								</div>

								{selectedType === 8 && (
									<div className="grid grid-cols-2 gap-4 mt-4">
										<div className="space-y-2">
											<Label>Include Blank Lanes</Label>
											<div className="flex items-center gap-2 h-10 px-3 rounded-md border bg-muted/30">
												<Switch
													checked={includeBlankLanes}
													onCheckedChange={setIncludeBlankLanes}
												/>
												<span className="text-xs">
													{includeBlankLanes ? "Yes" : "No"}
												</span>
											</div>
										</div>
										<div className="space-y-2">
											<Label>Page Break Every 6 Events</Label>
											<div className="flex items-center gap-2 h-10 px-3 rounded-md border bg-muted/30">
												<Switch
													checked={breakEverySixEvents}
													onCheckedChange={setBreakEverySixEvents}
												/>
												<span className="text-xs">
													{breakEverySixEvents ? "Yes" : "No"}
												</span>
											</div>
										</div>
									</div>
								)}

								<div className="p-4 bg-muted/50 rounded-lg space-y-3">
									<h4 className="text-xs font-bold uppercase tracking-tight flex items-center gap-2">
										<Filter className="h-3 w-3" />
										Summary
									</h4>
									<div className="text-sm space-y-1">
										<p>
											<span className="text-muted-foreground">Type:</span>{" "}
											{reportTypes.find((r) => r.id === selectedType)?.name}
										</p>
										<p>
											<span className="text-muted-foreground">Target:</span>{" "}
											{teamFilter || "All Teams"}
										</p>
										<p>
											<span className="text-muted-foreground">Filters:</span>{" "}
											{genderFilter}, {ageGroupFilter}
										</p>
										<p>
											<span className="text-muted-foreground">Style:</span>{" "}
											{zebraStriping ? "Zebra Striped" : "Standard"}
										</p>
									</div>
								</div>

								<div className="flex items-center justify-between p-4 bg-primary/5 rounded-lg border border-primary/10">
									<div className="space-y-0.5">
										<h4 className="text-sm font-medium">Preview Mode</h4>
										<p className="text-[10px] text-muted-foreground">
											View as interactive HTML instead of PDF
										</p>
									</div>
									<Switch
										checked={htmlPreviewMode}
										onCheckedChange={setHtmlPreviewMode}
										data-testid="html-preview-toggle"
									/>
								</div>
							</CardContent>
							<CardFooter className="flex flex-col gap-3 p-6 bg-muted/5 border-t">
								<div className="flex w-full gap-3">
									<Button
										variant="outline"
										className="flex-1 h-12"
										onClick={addToPack}
										data-testid="add-to-pack-button"
									>
										<Plus className="mr-2 h-4 w-4" />
										Add to Pack
									</Button>
									<Button
										className="flex-1 h-12"
										onClick={handleGenerate}
										disabled={isGenerating}
										data-testid="generate-report-button"
									>
										{isGenerating ? (
											<>
												<Loader2 className="mr-2 h-4 w-4 animate-spin" />
												Wait...
											</>
										) : (
											<>
												<Download className="mr-2 h-4 w-4" />
												{htmlPreviewMode ? "Open HTML" : "Download PDF"}
											</>
										)}
									</Button>
								</div>
							</CardFooter>
						</Card>
					)}
				</div>
			</div>

			<div id="report-builder" className="space-y-4">
				<Card
					className="shadow-lg border-primary/20"
					data-testid="report-builder-card"
					data-report-status={isBundling ? "bundling" : "idle"}
				>
					<CardHeader className="bg-primary/5 border-b rounded-t-xl">
						<div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
							<div className="flex items-center gap-2">
								<Package className="h-6 w-6 text-primary" />
								<div>
									<CardTitle>Custom Report Pack Builder</CardTitle>
									<CardDescription>
										Combine multiple reports into a single ZIP bundle.
									</CardDescription>
								</div>
							</div>
							<div className="flex gap-2">
								<Button
									variant="outline"
									size="sm"
									onClick={clearPack}
									disabled={customPack.length === 0 || isBundling}
									data-testid="clear-pack-button"
								>
									{" "}
									<Trash2 className="mr-2 h-4 w-4" />
									Clear
								</Button>
								<Button
									size="sm"
									onClick={handleGenerateBundle}
									disabled={customPack.length === 0 || isBundling}
									data-testid="generate-bundle-button"
								>
									<Download className="mr-2 h-4 w-4" />
									{isBundling ? "Bundling..." : "Generate ZIP"}
								</Button>
							</div>
						</div>
						<CardDescription>
							{customPack.length} Reports in custom pack
						</CardDescription>
					</CardHeader>
					<CardContent className="p-0">
						<ScrollArea className="h-[500px]">
							{customPack.length === 0 ? (
								<div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground gap-4">
									<Package className="h-12 w-12 opacity-20" />
									<p>
										Your pack is empty. Use "Apply to Builder" or "Add to Pack"
										to get started.
									</p>
								</div>
							) : (
								<div className="divide-y border-b">
									{customPack.map((item, index) => (
										<div key={item.id} className="p-6 hover:bg-muted/50">
											<div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
												<div className="md:col-span-1">
													<div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs">
														{index + 1}
													</div>
												</div>
												<div className="md:col-span-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
													<div className="space-y-1.5">
														<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
															Type
														</Label>
														<Select
															value={item.type.toString()}
															onValueChange={(v) =>
																updatePackItem(item.id, {
																	type: Number.parseInt(v, 10),
																})
															}
														>
															<SelectTrigger className="h-8 text-xs">
																<SelectValue />
															</SelectTrigger>
															<SelectContent>
																{reportTypes.map((t) => (
																	<SelectItem
																		key={t.id}
																		value={t.id.toString()}
																	>
																		{t.name}
																	</SelectItem>
																))}
															</SelectContent>
														</Select>
													</div>
													<div className="space-y-1.5">
														<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
															Title
														</Label>
														<Input
															value={item.title}
															onChange={(e) =>
																updatePackItem(item.id, {
																	title: e.target.value,
																})
															}
															placeholder="Report Title"
															className="h-8 text-xs"
														/>
													</div>
													<div className="space-y-1.5">
														<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
															Team
														</Label>
														<Select
															value={item.teamFilter}
															onValueChange={(v) =>
																updatePackItem(item.id, { teamFilter: v })
															}
														>
															<SelectTrigger className="h-8 text-xs">
																<SelectValue />
															</SelectTrigger>
															<SelectContent>
																<SelectItem value="All Teams">
																	All Teams
																</SelectItem>
																{initialTeams.map((team) => (
																	<SelectItem key={team.id} value={team.name}>
																		{team.name}
																	</SelectItem>
																))}
															</SelectContent>
														</Select>
													</div>
													<div className="space-y-1.5">
														<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
															Gender
														</Label>
														<Select
															value={item.genderFilter}
															onValueChange={(v) =>
																updatePackItem(item.id, { genderFilter: v })
															}
														>
															<SelectTrigger className="h-8 text-xs">
																<SelectValue />
															</SelectTrigger>
															<SelectContent>
																{genderOptions.map((opt) => (
																	<SelectItem key={opt} value={opt}>
																		{opt}
																	</SelectItem>
																))}
															</SelectContent>
														</Select>
													</div>
													<div className="space-y-1.5">
														<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
															Age Group
														</Label>
														<Select
															value={item.ageGroupFilter}
															onValueChange={(v) =>
																updatePackItem(item.id, { ageGroupFilter: v })
															}
														>
															<SelectTrigger className="h-8 text-xs">
																<SelectValue />
															</SelectTrigger>
															<SelectContent>
																{ageGroupOptions.map((opt) => (
																	<SelectItem key={opt} value={opt}>
																		{opt}
																	</SelectItem>
																))}
															</SelectContent>
														</Select>
													</div>
													{item.type === 8 ? (
														<>
															<div className="flex flex-col justify-center gap-1.5">
																<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
																	Blank
																</Label>
																<div className="flex items-center h-8">
																	<Switch
																		checked={item.includeBlankLanes !== false}
																		onCheckedChange={(v) =>
																			updatePackItem(item.id, {
																				includeBlankLanes: v,
																			})
																		}
																		className="scale-75 origin-left"
																	/>
																</div>
															</div>
															<div className="flex flex-col justify-center gap-1.5">
																<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
																	Break 6
																</Label>
																<div className="flex items-center h-8">
																	<Switch
																		checked={item.breakEverySixEvents !== false}
																		onCheckedChange={(v) =>
																			updatePackItem(item.id, {
																				breakEverySixEvents: v,
																			})
																		}
																		className="scale-75 origin-left"
																	/>
																</div>
															</div>
														</>
													) : (
														<div className="flex flex-col justify-center gap-1.5">
															<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
																Zebra
															</Label>
															<div className="flex items-center h-8">
																<Switch
																	checked={item.zebraStriping}
																	onCheckedChange={(v) =>
																		updatePackItem(item.id, {
																			zebraStriping: v,
																		})
																	}
																	className="scale-75 origin-left"
																/>
															</div>
														</div>
													)}
												</div>
												<div className="md:col-span-1 flex justify-end">
													<Button
														variant="ghost"
														size="icon"
														onClick={() => removeFromPack(item.id)}
														className="text-muted-foreground hover:text-destructive h-8 w-8"
													>
														<Trash2 className="h-4 w-4" />
													</Button>
												</div>
											</div>
										</div>
									))}
								</div>
							)}
						</ScrollArea>
					</CardContent>
				</Card>
			</div>

			{isBundling && (
				<div className="fixed bottom-6 right-6 w-80 bg-background border rounded-xl shadow-2xl p-6 z-50 animate-in slide-in-from-bottom-4">
					<div className="space-y-4">
						<div className="flex items-center justify-between">
							<h3 className="font-bold text-sm">Generating Bundle</h3>
							<Loader2 className="h-4 w-4 animate-spin text-primary" />
						</div>
						<div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
							<div
								className="bg-primary h-full transition-all duration-300"
								style={{ width: `${jobProgress}%` }}
							/>
						</div>
						<p className="text-xs text-muted-foreground text-center">
							{jobMessage} ({Math.round(jobProgress)}%)
						</p>
					</div>
				</div>
			)}
		</div>
	);
}
