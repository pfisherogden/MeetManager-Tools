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
import { generateReport, generateReportBundle, getJobStatus, getTeams } from "@/app/actions";
import { Badge } from "@/components/ui/badge";
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
		id: 1,
		name: "Psych Sheet",
		description: "List of entries by event with seed times.",
	},
	{
		id: 2,
		name: "Meet Entries",
		description: "Individual and relay entries grouped by team.",
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
		id: 3,
		name: "Lineup Sheets",
		description: "Heat and lane assignments for parent volunteers.",
	},
	{
		id: 4,
		name: "Meet Results",
		description: "Final times, places, and points by event.",
	},
	{
		id: 5,
		name: "Meet Program (HTML)",
		description: "Interactive HTML view of the 2-column meet program.",
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

interface CustomPackItem {
	id: string;
	type: number;
	title: string;
	teamFilter: string;
	genderFilter: string;
	ageGroupFilter: string;
	zebraStriping: boolean;
}

export function ReportsManager() {
	const [selectedType, setSelectedType] = useState<number | null>(null);
	const [title, setTitle] = useState("");
	const [teamFilter, setTeamFilter] = useState("");
	const [isGenerating, setIsGenerating] = useState(false);
	const [isBundling, setIsBundling] = useState(false);
	const [customPack, setCustomPack] = useState<CustomPackItem[]>([]);
	const [zebraStriping, setZebraStriping] = useState(false);
	const [htmlPreviewMode, setHtmlPreviewMode] = useState(false);
	const [presetTeamFilter, setPresetTeamFilter] = useState("All Teams");
	const [rendererType, setRendererType] = useState<RendererType>(
		RendererType.RENDERER_TYPE_PLAYWRIGHT,
	);

	// Multi-step generation state
	const [activeJobId, setJobId] = useState<string | null>(null);
	const [jobProgress, setJobProgress] = useState(0);
	const [jobMessage, setJobMessage] = useState("");
	const pollingInterval = useRef<NodeJS.Timeout | null>(null);
	const downloadTriggered = useRef<string | null>(null);

	// Improved Team Filter State
	const [initialTeams, setTeams] = useState<{ id: number; name: string }[]>([]);
	const [teamFilterOpen, setTeamFilterOpen] = useState(false);
	const [presetTeamOpen, setPresetTeamOpen] = useState(false);

	useEffect(() => {
		getTeams().then((res) => {
			if (res.teams) setTeams(res.teams);
		});
	}, []);

	// Clear polling on unmount
	useEffect(() => {
		return () => {
			if (pollingInterval.current) clearInterval(pollingInterval.current);
		};
	}, []);

	const startPolling = (jobId: string, filename: string) => {
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

					if (status.bundleUrl && downloadTriggered.current !== jobId) {
						downloadTriggered.current = jobId;
						window.location.href = status.bundleUrl;
						toast.success("Custom pack generated successfully");
					}
					setJobId(null);
					setIsBundling(false);
				} else if (status.status === 2) {
					// PROCESSING
					setJobProgress(status.progress * 100);
					setJobMessage(status.message || "Processing...");
				} else if (status.status === 4) {
					// FAILED
					if (pollingInterval.current) clearInterval(pollingInterval.current);
					setJobId(null);
					setIsBundling(false);
					toast.error(`Generation failed: ${status.message}`);
				}
			} catch (error) {
				console.error("Polling error:", error);
			}
		}, 3000);
	};

	const handleActionError = (error: unknown, fallbackMessage: string) => {
		console.error(`${fallbackMessage}:`, error);
		const message = error instanceof Error ? error.message : fallbackMessage;
		toast.error(message);
	};

	const addToPack = () => {
		if (!selectedType) return;

		const typeInfo = reportTypes.find((r) => r.id === selectedType);
		const newItem: CustomPackItem = {
			id: crypto.randomUUID(),
			type: selectedType,
			title: title || typeInfo?.name || "Report",
			teamFilter,
			genderFilter: "Mixed",
			ageGroupFilter: "Open",
			zebraStriping,
		};

		setCustomPack([...customPack, newItem]);
		toast.success("Added to custom pack");
	};

	const updatePackItem = (id: string, updates: Partial<CustomPackItem>) => {
		setCustomPack(
			customPack.map((item) => (item.id === id ? { ...item, ...updates } : item)),
		);
	};

	const removeFromPack = (id: string) => {
		setCustomPack(customPack.filter((item) => item.id !== id));
	};

	const clearPack = () => {
		setCustomPack([]);
	};

	const handleApplyPreset = (preset: any) => {
		const targetTeam = presetTeamFilter === "All Teams" ? "" : presetTeamFilter;
		const newItems: CustomPackItem[] = preset.reports.map((r: any) => ({
			id: crypto.randomUUID(),
			type: r.type,
			title: r.title,
			teamFilter: r.teamFilter || targetTeam,
			genderFilter: r.genderFilter || "Mixed",
			ageGroupFilter: r.ageGroupFilter || "Open",
			zebraStriping: r.zebraStriping || false,
		}));

		setCustomPack(newItems);
		toast.success(`Applied ${preset.name} preset`);

		// Scroll to builder
		const builder = document.getElementById("custom-builder");
		if (builder) builder.scrollIntoView({ behavior: "smooth" });
	};

	const generateCustomPack = async () => {
		if (customPack.length === 0) return;

		setIsBundling(true);
		try {
			const result = await generateReportBundle(
				customPack,
				"custom_report_pack.zip",
				rendererType,
			);
			if (result.success && result.jobId) {
				startPolling(result.jobId, "custom_report_pack.zip");
			} else if (result.success && result.bundleUrl) {
				window.location.href = result.bundleUrl;
				setIsBundling(false);
			} else {
				throw new Error(result.message || "Failed to generate bundle");
			}
		} catch (error: unknown) {
			handleActionError(error, "Custom pack generation failed");
			setIsBundling(false);
		}
	};

	const handleGenerate = async () => {
		if (!selectedType) return;
		setIsGenerating(true);

		const typeInfo = reportTypes.find((r) => r.id === selectedType);
		const reportTitle = title || typeInfo?.name || "Report";

		try {
			const result = await generateReport(
				selectedType,
				reportTitle,
				teamFilter,
				"Mixed",
				"Open",
				2,
				true,
				zebraStriping,
				rendererType,
				htmlPreviewMode,
			);

			if (result.success) {
				if ((selectedType === 5 || htmlPreviewMode) && result.htmlContent) {
					// Create a Blob from the HTML content
					const blob = new Blob([result.htmlContent], { type: "text/html" });
					const url = URL.createObjectURL(blob);
					const newTab = window.open(url, "_blank");

					if (newTab) {
						toast.success("HTML Preview opened in new tab");
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

					const blob = new Blob([bytes], {
						type: "application/pdf",
					});
					const url = URL.createObjectURL(blob);
					const a = document.createElement("a");
					a.href = url;
					a.download = result.filename || "report.pdf";
					document.body.appendChild(a);
					a.click();
					document.body.removeChild(a);
					URL.revokeObjectURL(url);
					toast.success("Report generated successfully");
				}
			}
		} catch (error: unknown) {
			handleActionError(error, "Generation failed");
		} finally {
			setIsGenerating(false);
		}
	};

	const reportPresets = [
		{
			id: "meet-ready",
			name: "Default Meet Pack",
			description: "Program, Timer Sheets, and Judge Sheets",
			reports: [
				{ type: 5, title: "Meet Program (HTML)" },
				{ type: 8, title: "Lane Timer Sheets" },
				{ type: 9, title: "S&T Judge Sheets" },
			],
		},
		{
			id: "official-results",
			name: "Results Pack",
			description: "Full results and score summaries",
			reports: [
				{ type: 4, title: "Official Meet Results" },
				{ type: 4, title: "Team Scores", zebraStriping: true },
			],
		},
	];

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
											size="sm"
											className="h-8 min-w-[120px] justify-between"
										>
											{presetTeamFilter}
											<ChevronsUpDown className="ml-2 h-3 w-3 opacity-50" />
										</Button>
									</PopoverTrigger>
									<PopoverContent className="w-[200px] p-0">
										<Command>
											<CommandInput placeholder="Filter by team..." />
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
							Commonly used combinations of reports
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-4">
						{reportPresets.map((preset) => (
							<div
								key={preset.id}
								className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/5 transition-colors"
							>
								<div className="space-y-1">
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

				<Card className="shadow-lg" data-testid="report-configuration-card">
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
								value={
									rendererType === RendererType.RENDERER_TYPE_UNSPECIFIED
										? RendererType.RENDERER_TYPE_PLAYWRIGHT.toString()
										: rendererType.toString()
								}
								onValueChange={(v) =>
									setRendererType(Number.parseInt(v, 10) as RendererType)
								}
							>
								<SelectTrigger className="w-full" data-testid="rendering-engine-selector">
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
									{selectedType === 5 || htmlPreviewMode ? "View HTML" : "Download PDF"}
								</>
							)}
						</Button>
					</CardFooter>
				</Card>
			</div>

			<Card id="custom-builder" className="shadow-lg border-primary/30">
				<CardHeader className="bg-primary/5 border-b rounded-t-xl">
					<div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
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
						<div className="flex flex-wrap items-center gap-4 lg:gap-6">
							<div className="flex flex-col gap-1 min-w-[140px]">
								<span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
									Rendering Engine
								</span>
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
							<div className="flex items-center gap-4 flex-1 justify-between lg:justify-end">
								{customPack.length > 0 && (
									<Button
										variant="ghost"
										size="sm"
										onClick={clearPack}
										className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 px-2"
										data-testid="clear-pack-button"
									>
										<Trash2 className="h-4 w-4 mr-1" />
										Clear All
									</Button>
								)}
								<div className="text-right">
									<p className="text-sm font-medium">
										{customPack.length} Reports
									</p>
									<p className="text-[10px] text-muted-foreground leading-tight">
										{activeJobId ? jobMessage : "Bundled as ZIP"}
									</p>
								</div>
								<Button
									onClick={generateCustomPack}
									disabled={isBundling || customPack.length === 0}
									size="sm"
									className="shadow-md min-w-[150px] lg:min-w-[180px] h-9"
								>
									{isBundling ? (
										<>
											<Loader2 className="mr-2 h-4 w-4 animate-spin" />
											{activeJobId ? `${Math.round(jobProgress)}%` : "Wait..."}
										</>
									) : (
										<>
											<Download className="mr-2 h-4 w-4" />
											Generate ZIP
										</>
									)}
								</Button>
							</div>
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
