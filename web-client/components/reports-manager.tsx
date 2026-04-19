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
import { handleActionError } from "@/lib/error-handler";
import {
	JobStatus,
	RendererType,
} from "@/lib/proto/meetmanager/v1/meet_manager";
import type { Team as UITeam } from "@/lib/swim-meet-types";
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
		description: "Timer sheets grouped by physical lane (10 entries per page).",
	},
	{
		id: 9,
		name: "S&T Judge Sheets",
		description: "Meet Program format with dedicated lines for DQ codes.",
	},
];

type CustomPackItem = {
	id: string;
	type: number;
	title: string;
	teamFilter: string;
	genderFilter: string;
	ageGroupFilter: string;
	zebraStriping: boolean;
};

interface ReportsManagerProps {
	initialTeams?: UITeam[];
}

export function ReportsManager({ initialTeams = [] }: ReportsManagerProps) {
	const [selectedType, setSelectedType] = useState<number>(0);
	const [title, setTitle] = useState("");
	const [teamFilter, setTeamFilter] = useState("");
	const [isGenerating, setIsGenerating] = useState(false);
	const [isBundling, setIsBundling] = useState(false);
	const [customPack, setCustomPack] = useState<CustomPackItem[]>([]);
	const [zebraStriping, setZebraStriping] = useState(false);
	const [presetTeamFilter, setPresetTeamFilter] = useState("All Teams");
	const [rendererType, setRendererType] = useState<RendererType>(
		RendererType.RENDERER_TYPE_PLAYWRIGHT,
	);

	// Async Job State
	const [activeJobId, setJobId] = useState<string | null>(null);
	const [jobProgress, setJobProgress] = useState(0);
	const [jobMessage, setJobMessage] = useState("");
	const pollingInterval = useRef<NodeJS.Timeout | null>(null);
	const downloadTriggered = useRef<string | null>(null);

	// Improved Team Filter State
	const [teamFilterOpen, setTeamFilterOpen] = useState(false);
	const [presetTeamOpen, setPresetTeamOpen] = useState(false);

	const addToPack = () => {
		const reportName =
			reportTypes.find((r) => r.id === selectedType)?.name || "";
		const newItem: CustomPackItem = {
			id: crypto.randomUUID(),
			type: selectedType,
			title: title || reportName,
			teamFilter: teamFilter,
			genderFilter: "Mixed",
			ageGroupFilter: "Open",
			zebraStriping: zebraStriping,
		};
		setCustomPack([...customPack, newItem]);
		toast.success("Added to custom pack");
	};

	const removeFromPack = (id: string) => {
		setCustomPack(customPack.filter((item) => item.id !== id));
	};

	const clearPack = () => {
		if (customPack.length === 0) return;
		setCustomPack([]);
		toast.success("Cleared custom pack");
	};

	const updatePackItem = (id: string, updates: Partial<CustomPackItem>) => {
		setCustomPack(
			customPack.map((item) =>
				item.id === id ? { ...item, ...updates } : item,
			),
		);
	};

	const startPolling = (jobId: string, filename: string) => {
		setJobId(jobId);
		setJobProgress(0);
		setJobMessage("Starting generation...");

		// Reset trigger for new job
		if (downloadTriggered.current === jobId) {
			downloadTriggered.current = null;
		}

		if (pollingInterval.current) clearInterval(pollingInterval.current);

		pollingInterval.current = setInterval(async () => {
			try {
				const status = await getJobStatus(jobId);

				// If status check failed or is somehow null, stop
				if (!status) return;

				setJobProgress(status.progress * 100);
				setJobMessage(status.message || "Processing...");

				if (status.status === JobStatus.JOB_STATUS_COMPLETED) {
					// CRITICAL: Clear interval FIRST to prevent re-entry
					if (pollingInterval.current) {
						clearInterval(pollingInterval.current);
						pollingInterval.current = null;
					}

					// Only trigger download once per jobId
					if (downloadTriggered.current !== jobId) {
						downloadTriggered.current = jobId;
						setJobId(null);
						setIsBundling(false);

						if (status.bundleUrl) {
							const downloadUrl = status.bundleUrl.startsWith("http")
								? status.bundleUrl
								: `${window.location.origin}${status.bundleUrl}`;

							const a = document.createElement("a");
							a.href = downloadUrl;
							a.download = filename;
							document.body.appendChild(a);
							a.click();
							document.body.removeChild(a);
							toast.success("Custom pack generated successfully");
						}
					}
				} else if (status.status === JobStatus.JOB_STATUS_FAILED) {
					if (pollingInterval.current) {
						clearInterval(pollingInterval.current);
						pollingInterval.current = null;
					}
					setJobId(null);
					setIsBundling(false);
					toast.error(`Generation failed: ${status.message}`);
				}
			} catch (error) {
				console.error("Polling error:", error);
			}
		}, 3000);
	};

	useEffect(() => {
		return () => {
			if (pollingInterval.current) clearInterval(pollingInterval.current);
		};
	}, []);

	const generateCustomPack = async () => {
		if (customPack.length === 0) {
			toast.error("Pack is empty");
			return;
		}
		setIsBundling(true);
		try {
			const timestamp = new Date()
				.toISOString()
				.replace(/[:.]/g, "-")
				.slice(0, 19);
			const suggestedName = `reports_${timestamp}_${customPack.length}_items.zip`;
			const result = await generateReportBundle(
				customPack,
				suggestedName,
				rendererType,
			);

			if (result.success && result.jobId) {
				startPolling(result.jobId, suggestedName);
				toast.info("Report generation started in background...");
			} else if (result.success && result.bundleUrl) {
				// Fallback for immediate success
				const downloadUrl = result.bundleUrl.startsWith("http")
					? result.bundleUrl
					: `${window.location.origin}${result.bundleUrl}`;

				const a = document.createElement("a");
				a.href = downloadUrl;
				a.download = result.filename || suggestedName;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				toast.success("Custom pack generated successfully");
				setIsBundling(false);
			} else {
				throw new Error(result.message || "Failed to generate bundle");
			}
		} catch (error: unknown) {
			handleActionError(error, "Custom pack generation failed");
			setIsBundling(false);
		}
	};

	const reportPresets = [
		{
			id: "default_pack",
			name: "Default Meet Pack",
			description:
				"Coaches, S&T Judges, Lane Timers, and Posting/Computer programs.",
			reports: [
				{
					type: 4,
					title: "Coaches Meet Program",
					columnsOnPage: 2,
					showRelaySwimmers: true,
				},
				{
					type: 9,
					title: "S&T Judge Program",
					columnsOnPage: 2,
					showRelaySwimmers: true,
					zebraStriping: true,
				},
				{
					type: 8,
					title: "Lane Timer Sheets",
				},
				{
					type: 4,
					title: "Computer/Posting Program",
					columnsOnPage: 2,
					showRelaySwimmers: false,
				},
			],
		},
		{
			id: "coaches",
			name: "Coaches Bundle",
			description: "Full meet program for all genders/ages (2-column).",
			reports: [
				{
					type: 4,
					title: "Coaches Meet Program",
					columnsOnPage: 2,
					showRelaySwimmers: true,
				},
			],
		},
		{
			id: "compact",
			name: "Compact Program",
			description: "Single-column program without relay swimmers.",
			reports: [
				{
					type: 4,
					title: "Compact Meet Program",
					columnsOnPage: 1,
					showRelaySwimmers: false,
				},
			],
		},
		{
			id: "board",
			name: "Board Postings",
			description: "Filtered programs for Girls, Boys (inc Mixed).",
			reports: [
				{
					type: 4,
					title: "Girls Meet Program for Board",
					genderFilter: "Girls",
					columnsOnPage: 2,
				},
				{
					type: 4,
					title: "Boys & Mixed Meet Program for Board",
					genderFilter: "Boys",
					columnsOnPage: 2,
				},
			],
		},
		{
			id: "lineups",
			name: "Lineup Sheets",
			description: "Single team lineups by age/gender.",
			reports: ["Girls", "Boys"].flatMap((gender) =>
				["6 & under", "7-8", "9-10", "11-12", "13-14", "15-18"].map((age) => ({
					type: 2,
					title: `Line Up Report - ${gender}, ${age}`,
					genderFilter: gender,
					ageGroupFilter: age,
				})),
			),
		},
	];

	const handleApplyPreset = (preset: (typeof reportPresets)[0]) => {
		const targetTeam = presetTeamFilter === "All Teams" ? "" : presetTeamFilter;
		const newItems: CustomPackItem[] = preset.reports.map((r: any) => ({
			id: crypto.randomUUID(),
			type: r.type,
			title: r.title,
			teamFilter: r.teamFilter || targetTeam,
			genderFilter: r.genderFilter || "Mixed",
			ageGroupFilter: r.ageGroupFilter || "Open",
			zebraStriping: zebraStriping,
		}));
		setCustomPack([...customPack, ...newItems]);
		toast.success(`Applied ${preset.name} to builder`);
		document
			.getElementById("custom-builder")
			?.scrollIntoView({ behavior: "smooth" });
	};

	const handleGenerate = async () => {
		setIsGenerating(true);
		try {
			const reportName =
				reportTypes.find((r) => r.id === selectedType)?.name || "Report";
			const result = await generateReport(
				selectedType,
				title || reportName,
				teamFilter,
				undefined,
				undefined,
				2,
				true,
				zebraStriping,
				rendererType,
			);

			if (result.success) {
				if (selectedType === 5 && result.htmlContent) {
					// Open HTML content in a new tab
					const newTab = window.open("", "_blank");
					if (newTab) {
						newTab.document.write(result.htmlContent);
						newTab.document.close();
						toast.success("HTML Program opened in new tab");
					} else {
						toast.error("Pop-up blocked. Please allow pop-ups for this site.");
					}
				} else if (result.pdfContentBase64) {
					// Decode base64 to binary
					const binaryString = window.atob(result.pdfContentBase64);
					const bytes = new Uint8Array(binaryString.length);
					for (let i = 0; i < binaryString.length; i++) {
						bytes[i] = binaryString.charCodeAt(i);
					}

					if (bytes.length === 0) {
						toast.error("Generated PDF was empty. Please try again.");
						return;
					}

					const blob = new Blob([bytes], {
						type: "application/pdf",
					});
					const url = URL.createObjectURL(blob);
					const a = document.createElement("a");
					a.href = url;
					a.download =
						result.filename ||
						`${reportName.toLowerCase().replace(/\s+/g, "_")}.pdf`;
					document.body.appendChild(a);
					a.click();
					document.body.removeChild(a);
					URL.revokeObjectURL(url);
					toast.success("Report generated successfully");
				}
			} else {
				throw new Error(result.message || "Failed to generate report");
			}
		} catch (error: unknown) {
			handleActionError(error, "Generation failed");
		} finally {
			setIsGenerating(false);
		}
	};

	return (
		<div className="flex-1 p-6 space-y-8 overflow-y-auto">
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				{reportTypes.map((report) => (
					<Card
						key={report.id}
						data-testid={`report-card-${report.name.toLowerCase().replace(/\s+/g, "-")}`}
						className={`cursor-pointer transition-all duration-200 border-2 ${
							selectedType === report.id
								? "border-primary bg-primary/5"
								: "hover:border-primary/50"
						}`}
						onClick={() => setSelectedType(report.id)}
					>
						<CardHeader className="pb-2">
							<div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mb-2">
								<FileText className="h-5 w-5 text-primary" />
							</div>
							<CardTitle className="text-lg">{report.name}</CardTitle>
						</CardHeader>
						<CardContent>
							<CardDescription>{report.description}</CardDescription>
						</CardContent>
					</Card>
				))}
			</div>

			<div className="grid grid-cols-1 md:grid-cols-2 gap-8">
				<Card className="shadow-lg">
					<CardHeader>
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-2">
								<Package className="h-5 w-5 text-primary" />
								<CardTitle>Report Presets</CardTitle>
							</div>
							<div className="flex items-center gap-2">
								<Label
									htmlFor="preset-team"
									className="text-xs text-muted-foreground whitespace-nowrap"
								>
									Target Team:
								</Label>
								<Popover open={presetTeamOpen} onOpenChange={setPresetTeamOpen}>
									<PopoverTrigger asChild>
										<Button
											variant="outline"
											role="combobox"
											aria-expanded={presetTeamOpen}
											className="h-8 w-40 justify-between text-xs"
										>
											{presetTeamFilter}
											<ChevronsUpDown className="ml-2 h-3 w-3 shrink-0 opacity-50" />
										</Button>
									</PopoverTrigger>
									<PopoverContent className="w-48 p-0">
										<Command>
											<CommandInput
												placeholder="Search teams..."
												className="h-8 text-xs"
											/>
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
																"mr-2 h-3 w-3",
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
																	"mr-2 h-3 w-3",
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
							Populate the builder with pre-configured bundles
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-4">
						{reportPresets.map((preset) => (
							<div
								key={preset.id}
								data-testid={`preset-${preset.id}`}
								className="flex items-center justify-between p-4 border rounded-lg bg-muted/10 hover:bg-muted/20 transition-colors"
							>
								<div>
									<h4 className="font-medium text-sm">{preset.name}</h4>
									<p className="text-[10px] text-muted-foreground">
										{preset.description}
									</p>
								</div>
								<Button
									variant="outline"
									size="sm"
									data-testid={`preset-apply-${preset.id}`}
									onClick={() => handleApplyPreset(preset)}
									className="text-xs h-8"
								>
									Apply to Builder
								</Button>
							</div>
						))}
					</CardContent>
				</Card>

				<Card className="shadow-lg">
					<CardHeader>
						<div className="flex items-center gap-2">
							<Settings2 className="h-5 w-5 text-primary" />
							<CardTitle>Report Configuration</CardTitle>
						</div>
						<CardDescription>
							Customize headers and filters for your report
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6">
						<div className="space-y-2">
							<Label htmlFor="title">Custom Report Title</Label>
							<Input
								id="title"
								placeholder={
									reportTypes.find((r) => r.id === selectedType)?.name ||
									"Meet Report"
								}
								value={title}
								onChange={(e) => setTitle(e.target.value)}
							/>
							<p className="text-xs text-muted-foreground">
								This will appear at the top of every page.
							</p>
						</div>

						<div className="space-y-2">
							<Label htmlFor="team">Team Filter (Optional)</Label>
							<div className="flex gap-2">
								<Popover open={teamFilterOpen} onOpenChange={setTeamFilterOpen}>
									<PopoverTrigger asChild>
										<Button
											variant="outline"
											role="combobox"
											data-testid="team-filter-trigger"
											aria-expanded={teamFilterOpen}
											className="w-full justify-between"
										>
											{teamFilter || "All Teams"}
											<ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
										</Button>
									</PopoverTrigger>
									<PopoverContent className="w-full p-0">
										<Command>
											<CommandInput placeholder="Search teams..." />
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
																teamFilter === "" ? "opacity-100" : "opacity-0",
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
								<Button
									variant="outline"
									size="icon"
									onClick={() => setTeamFilterOpen(true)}
								>
									<Filter className="h-4 w-4" />
								</Button>
							</div>
						</div>

						<div className="flex items-center justify-between p-4 border rounded-lg bg-muted/5">
							<div className="space-y-0.5">
								<Label htmlFor="zebra">Zebra Striping</Label>
								<p className="text-xs text-muted-foreground">
									Alternate background colors for entries
								</p>
							</div>
							<Switch
								id="zebra"
								checked={zebraStriping}
								onCheckedChange={setZebraStriping}
							/>
						</div>

						<div className="space-y-2">
							<Label>Rendering Engine</Label>
							<Select
								value={rendererType.toString()}
								onValueChange={(v) =>
									setRendererType(Number.parseInt(v, 10) as RendererType)
								}
							>
								<SelectTrigger className="w-full">
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
							<p className="text-[10px] text-muted-foreground">
								Playwright is faster for large reports; WeasyPrint generates
								smaller files.
							</p>
						</div>

						<div className="p-4 bg-muted/30 rounded-lg space-y-2">
							<h4 className="text-sm font-medium flex items-center gap-2">
								<Download className="h-4 w-4" />
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
									<span className="text-muted-foreground">Style:</span>{" "}
									{zebraStriping ? "Zebra Striped" : "Standard"}
								</p>
								<p>
									<span className="text-muted-foreground">Branding:</span>{" "}
									MM-Tools
								</p>
							</div>
						</div>
					</CardContent>
					<CardFooter className="bg-muted/10 border-t pt-6 gap-4">
						<Button
							className="flex-1 text-xs h-10"
							variant="outline"
							onClick={addToPack}
						>
							<Plus className="mr-2 h-4 w-4" />
							Add to Pack
						</Button>
						<Button
							className="flex-1 text-xs h-10"
							onClick={handleGenerate}
							disabled={isGenerating}
						>
							{isGenerating ? (
								<>
									<Loader2 className="mr-2 h-4 w-4 animate-spin" />
									Generating...
								</>
							) : (
								<>
									<Download className="mr-2 h-4 w-4" />
									{selectedType === 5 ? "View HTML" : "Download PDF"}
								</>
							)}
						</Button>
					</CardFooter>
				</Card>
			</div>

			<Card id="custom-builder" className="shadow-lg border-primary/30">
				<CardHeader className="bg-primary/5 border-b rounded-t-xl">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-2">
							<Package className="h-6 w-6 text-primary" />
							<div>
								<CardTitle>Custom Report Pack Builder</CardTitle>
								<CardDescription>
									Build a specialized bundle of multiple reports with individual
									filters
								</CardDescription>
							</div>
						</div>
						<div className="flex items-center gap-6">
							<div className="flex flex-col gap-1 min-w-[150px]">
								<span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
									Rendering Engine
								</span>
								<Select
									value={rendererType.toString()}
									onValueChange={(v) =>
										setRendererType(Number.parseInt(v, 10) as RendererType)
									}
								>
									<SelectTrigger className="h-8 text-xs">
										<SelectValue />
									</SelectTrigger>
									<SelectContent>
										<SelectItem
											value={RendererType.RENDERER_TYPE_PLAYWRIGHT.toString()}
										>
											Playwright
										</SelectItem>
										<SelectItem
											value={RendererType.RENDERER_TYPE_WEASYPRINT.toString()}
										>
											WeasyPrint
										</SelectItem>
									</SelectContent>
								</Select>
							</div>
							{customPack.length > 0 && (
								<Button
									variant="ghost"
									size="sm"
									onClick={clearPack}
									className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8"
									data-testid="clear-pack-button"
								>
									<Trash2 className="h-4 w-4 mr-1" />
									Clear All
								</Button>
							)}
							<div className="text-right">
								<p className="text-sm font-medium">
									{customPack.length} Reports Selected
								</p>
								<p className="text-xs text-muted-foreground">
									{activeJobId
										? jobMessage
										: "Will be delivered as a single ZIP file"}
								</p>
							</div>
							<Button
								onClick={generateCustomPack}
								disabled={isBundling || customPack.length === 0}
								size="lg"
								className="shadow-md min-w-[200px]"
							>
								{isBundling ? (
									<>
										<Loader2 className="mr-2 h-4 w-4 animate-spin" />
										{activeJobId
											? `${Math.round(jobProgress)}%`
											: "Initializing..."}
									</>
								) : (
									<>
										<Download className="mr-2 h-4 w-4" />
										Generate Bundle ZIP
									</>
								)}
							</Button>
						</div>
					</div>
				</CardHeader>
				<CardContent className="p-0">
					<ScrollArea className="h-[500px]">
						{customPack.length === 0 ? (
							<div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground gap-4">
								<Package className="h-12 w-12 opacity-20" />
								<p>
									Your pack is empty. Use "Apply to Builder" or "Add to Pack" to
									get started.
								</p>
							</div>
						) : (
							<div className="divide-y border-b">
								{customPack.map((item, index) => (
									<div
										key={item.id}
										className={cn(
											"p-6 transition-colors border-l-4",
											index % 2 === 0
												? "bg-card border-l-primary/40"
												: "bg-muted/30 border-l-muted-foreground/40",
											"hover:bg-primary/5",
										)}
									>
										<div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
											<div className="md:col-span-1 flex items-center justify-center">
												<div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm border border-primary/20">
													{index + 1}
												</div>
											</div>
											<div className="md:col-span-10 grid grid-cols-1 md:grid-cols-3 gap-4">
												<div className="space-y-2">
													<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
														Report Type
													</Label>
													<Select
														value={item.type.toString()}
														onValueChange={(v) =>
															updatePackItem(item.id, {
																type: Number.parseInt(v, 10),
															})
														}
													>
														<SelectTrigger className="h-9">
															<SelectValue />
														</SelectTrigger>
														<SelectContent>
															{reportTypes.map((t) => (
																<SelectItem key={t.id} value={t.id.toString()}>
																	{t.name}
																</SelectItem>
															))}
														</SelectContent>
													</Select>
												</div>
												<div className="space-y-2">
													<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
														Custom Title
													</Label>
													<Input
														value={item.title}
														onChange={(e) =>
															updatePackItem(item.id, { title: e.target.value })
														}
														placeholder="Report Title"
														className="h-9"
													/>
												</div>
												<div className="space-y-2">
													<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
														Team Filter
													</Label>
													<Popover>
														<PopoverTrigger asChild>
															<Button
																variant="outline"
																role="combobox"
																className="h-9 w-full justify-between font-normal"
															>
																{item.teamFilter || "All Teams"}
																<ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
															</Button>
														</PopoverTrigger>
														<PopoverContent className="w-full p-0">
															<Command>
																<CommandInput placeholder="Search teams..." />
																<CommandList>
																	<CommandEmpty>No team found.</CommandEmpty>
																	<CommandGroup>
																		<CommandItem
																			onSelect={() => {
																				updatePackItem(item.id, {
																					teamFilter: "",
																				});
																			}}
																		>
																			<Check
																				className={cn(
																					"mr-2 h-4 w-4",
																					item.teamFilter === ""
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
																					updatePackItem(item.id, {
																						teamFilter: team.name,
																					});
																				}}
																			>
																				<Check
																					className={cn(
																						"mr-2 h-4 w-4",
																						item.teamFilter === team.name
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
												<div className="space-y-2">
													<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
														Gender
													</Label>
													<Select
														value={item.genderFilter}
														onValueChange={(v) =>
															updatePackItem(item.id, { genderFilter: v })
														}
													>
														<SelectTrigger className="h-9">
															<SelectValue />
														</SelectTrigger>
														<SelectContent>
															<SelectItem value="Mixed">Mixed/All</SelectItem>
															<SelectItem value="Girls">Girls</SelectItem>
															<SelectItem value="Boys">Boys</SelectItem>
														</SelectContent>
													</Select>
												</div>
												<div className="space-y-2">
													<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
														Age Group
													</Label>
													<Select
														value={item.ageGroupFilter}
														onValueChange={(v) =>
															updatePackItem(item.id, { ageGroupFilter: v })
														}
													>
														<SelectTrigger className="h-9">
															<SelectValue />
														</SelectTrigger>
														<SelectContent>
															<SelectItem value="Open">Open/All</SelectItem>
															<SelectItem value="6 & under">
																6 & under
															</SelectItem>
															<SelectItem value="7-8">7-8</SelectItem>
															<SelectItem value="9-10">9-10</SelectItem>
															<SelectItem value="11-12">11-12</SelectItem>
															<SelectItem value="13-14">13-14</SelectItem>
															<SelectItem value="15-18">15-18</SelectItem>
														</SelectContent>
													</Select>
												</div>
												<div className="flex items-center gap-3 pt-6">
													<Switch
														id={`zebra-${item.id}`}
														checked={item.zebraStriping}
														onCheckedChange={(v) =>
															updatePackItem(item.id, { zebraStriping: v })
														}
													/>
													<Label
														htmlFor={`zebra-${item.id}`}
														className="text-xs font-medium"
													>
														Zebra Striping
													</Label>
												</div>
											</div>
											<div className="md:col-span-1 flex justify-end pt-6">
												<Button
													variant="ghost"
													size="icon"
													className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 h-9 w-9 transition-colors"
													onClick={() => removeFromPack(item.id)}
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
	);
}
