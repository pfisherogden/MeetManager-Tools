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

interface ReportsManagerProps {
	initialTeams?: { id: number; name: string }[];
}

export function ReportsManager({
	initialTeams: propTeams = [],
}: ReportsManagerProps) {
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
	const [_activeJobId, setJobId] = useState<string | null>(null);
	const [jobProgress, setJobProgress] = useState(0);
	const [jobMessage, setJobMessage] = useState("");
	const pollingInterval = useRef<NodeJS.Timeout | null>(null);
	const downloadTriggered = useRef<string | null>(null);

	// Improved Team Filter State
	const [initialTeams, setTeams] =
		useState<{ id: number; name: string }[]>(propTeams);
	const [teamFilterOpen, setTeamFilterOpen] = useState(false);
	const [presetTeamOpen, setPresetTeamOpen] = useState(false);

	useEffect(() => {
		if (propTeams.length > 0) {
			setTeams(propTeams);
		} else {
			getTeams().then((res) => {
				if (res.teams) setTeams(res.teams);
			});
		}
	}, [propTeams]);

	// Clear polling on unmount
	useEffect(() => {
		return () => {
			if (pollingInterval.current) clearInterval(pollingInterval.current);
		};
	}, []);

	const handleActionError = (error: unknown, fallbackMessage: string) => {
		const message = error instanceof Error ? error.message : fallbackMessage;
		toast.error(message);
	};

	const addToPack = () => {
		if (selectedType === null) return;

		const typeInfo = reportTypes.find((r) => r.id === selectedType);
		const newItem: CustomPackItem = {
			id: crypto.randomUUID(),
			type: selectedType,
			title: title || typeInfo?.name || "Report",
			teamFilter: teamFilter || "All Teams",
			genderFilter: "Both",
			ageGroupFilter: "All Ages",
			zebraStriping: zebraStriping,
		};
		setCustomPack([...customPack, newItem]);
		toast.success("Added to custom pack");
	};

	const removeFromPack = (id: string) => {
		setCustomPack(customPack.filter((item) => item.id !== id));
		toast.success("Removed from pack");
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
						toast.success("Custom pack generated successfully");
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

		const typeInfo = reportTypes.find((r) => r.id === selectedType);
		const reportTitle = title || typeInfo?.name || "Report";

		// Open blank window synchronously to prevent popup blocking in CI/headless
		let newTab: Window | null = null;
		if (selectedType === 5 || htmlPreviewMode) {
			newTab = window.open("about:blank", "_blank");
			if (newTab) {
				newTab.document.write(
					"<html><body><p>Generating report...</p></body></html>",
				);
				newTab.document.close();
			}
		}

		try {
			const result = await generateReport(
				selectedType,
				reportTitle,
				teamFilter,
				undefined, // genderFilter
				undefined, // ageGroupFilter
				2, // columnsOnPage
				true, // showRelaySwimmers
				zebraStriping,
				rendererType,
				htmlPreviewMode,
			);

			if (result.success) {
				if ((selectedType === 5 || htmlPreviewMode) && result.htmlContent) {
					if (newTab) {
						newTab.document.open();
						newTab.document.write(result.htmlContent);
						newTab.document.close();
						toast.success("HTML Program opened in new tab");
					} else {
						// Fallback if popup was blocked despite synchronous opening
						const blob = new Blob([result.htmlContent], { type: "text/html" });
						const url = URL.createObjectURL(blob);
						window.open(url, "_blank");
						toast.success("HTML Program opened in new tab");
					}
				} else if (result.pdfContentBase64) {
					// Close tab if it was opened but we got a PDF
					if (newTab) newTab.close();

					// Decode base64 to binary
					const binaryString = window.atob(result.pdfContentBase64);
					const len = binaryString.length;
					const bytes = new Uint8Array(len);
					for (let i = 0; i < len; i++) {
						bytes[i] = binaryString.charCodeAt(i);
					}

					const blob = new Blob([bytes], { type: "application/pdf" });
					const url = URL.createObjectURL(blob);
					const a = document.createElement("a");
					a.href = url;
					a.download = result.filename || "report.pdf";
					document.body.appendChild(a);
					a.click();
					document.body.removeChild(a);
					URL.revokeObjectURL(url);
					toast.success("Report generated successfully");
				} else {
					if (newTab) newTab.close();
					throw new Error("No report content received from server");
				}
			} else {
				if (newTab) newTab.close();
				throw new Error(result.message || "Failed to generate report");
			}
		} catch (error: unknown) {
			if (newTab) newTab.close();
			handleActionError(error, "Generation failed");
		} finally {
			setIsGenerating(false);
		}
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
				zebraStriping: item.zebraStriping,
				rendererType,
				htmlPreview: false,
			}));

			const result = await generateReportBundle(requests, "meet_report_bundle");

			if (result.success && result.jobId) {
				startPolling(result.jobId, result.filename || "bundle.zip");
			} else {
				throw new Error(result.message || "Failed to start bundling job");
			}
		} catch (error: unknown) {
			handleActionError(error, "Bundling failed");
			setIsBundling(false);
		}
	};

	const applyPreset = (preset: (typeof reportPresets)[0]) => {
		const newItems: CustomPackItem[] = preset.reports.map((r) => ({
			id: crypto.randomUUID(),
			type: r.type,
			title: r.title,
			teamFilter: presetTeamFilter === "All Teams" ? "" : presetTeamFilter,
			genderFilter: "Both",
			ageGroupFilter: "All Ages",
			zebraStriping: r.zebraStriping || false,
		}));
		setCustomPack([...customPack, ...newItems]);
		toast.success(`Applied ${preset.name} to builder`);

		// Scroll builder into view (if available in environment)
		const builder = document.getElementById("report-builder");
		if (builder && typeof builder.scrollIntoView === "function") {
			builder.scrollIntoView({ behavior: "smooth" });
		}
	};

	const reportPresets = [
		{
			id: "default",
			name: "Default Meet Pack",
			description: "Psych Sheets, Lineups, and Meet Program",
			reports: [
				{ type: 0, title: "Official Psych Sheet" },
				{ type: 2, title: "Team Lineup Sheets" },
				{ type: 4, title: "Standard Meet Program" },
			],
		},
		{
			id: "lineups",
			name: "Lineup Sheets",
			description: "Full set of heat/lane assignments",
			reports: Array.from({ length: 12 }, (_, i) => ({
				type: 2,
				title: `Lineup Sheet - Session ${i + 1}`,
			})),
		},
		{
			id: "timer-pack",
			name: "Timer & Judge Pack",
			description: "HTML Program, Timer Sheets, and Judge Sheets",
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
				{ type: 3, title: "Official Meet Results" },
				{ type: 3, title: "Team Scores", zebraStriping: true },
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
							Commonly used combinations of reports for specific meet roles.
						</CardDescription>
					</CardHeader>
					<CardContent className="grid gap-4">
						{reportPresets.map((preset) => (
							<div
								key={preset.id}
								className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/5 transition-colors"
							>
								<div className="space-y-1">
									<h4 className="text-sm font-semibold">{preset.name}</h4>
									<p className="text-[10px] text-muted-foreground italic">
										{preset.description}
									</p>
									<div className="flex gap-2 mt-2">
										{preset.reports.slice(0, 3).map((r, _i) => (
											<span
												key={`${r.type}-${r.title}`}
												className="px-2 py-0.5 bg-muted rounded text-[9px] font-medium"
											>
												{r.title}
											</span>
										))}
									</div>
								</div>
								<Button
									size="sm"
									variant="secondary"
									className="ml-4 h-8"
									onClick={() => applyPreset(preset)}
									data-testid={`preset-apply-${preset.id.split("-")[0]}`}
								>
									Apply to Builder
								</Button>
							</div>
						))}
					</CardContent>
				</Card>

				{selectedType !== null && (
					<Card data-testid="report-configuration-card" className="shadow-lg">
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
								<Popover open={teamFilterOpen} onOpenChange={setTeamFilterOpen}>
									<PopoverTrigger asChild>
										<Button
											variant="outline"
											className="w-full justify-between"
											role="combobox"
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
								data-testid="generate-report-button"
							>
								{isGenerating ? (
									<>
										<Loader2 className="mr-2 h-4 w-4 animate-spin" />
										Generating...
									</>
								) : (
									<>
										<Download className="mr-2 h-4 w-4" />
										{selectedType === 5 || htmlPreviewMode
											? "View HTML"
											: "Download PDF"}
									</>
								)}
							</Button>
						</CardFooter>
					</Card>
				)}
			</div>

			<div id="report-builder" className="space-y-4">
				<Card className="shadow-lg border-primary/20">
					<CardHeader className="bg-primary/5">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-2">
								<Settings2 className="h-5 w-5 text-primary" />
								<CardTitle>Custom Report Pack Builder</CardTitle>
							</div>
							<div className="flex gap-2">
								<Button
									variant="outline"
									size="sm"
									onClick={clearPack}
									disabled={customPack.length === 0 || isBundling}
								>
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
													<div className="space-y-2">
														<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
															Custom Title
														</Label>
														<Input
															value={item.title}
															onChange={(e) =>
																updatePackItem(item.id, {
																	title: e.target.value,
																})
															}
															placeholder="Report Title"
															className="h-9"
														/>
													</div>
													<div className="space-y-2">
														<Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
															Team Filter
														</Label>
														<Select
															value={item.teamFilter}
															onValueChange={(v) =>
																updatePackItem(item.id, { teamFilter: v })
															}
														>
															<SelectTrigger className="h-9">
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
												</div>
												<div className="md:col-span-1 flex justify-end">
													<Button
														variant="ghost"
														size="icon"
														onClick={() => removeFromPack(item.id)}
														className="text-muted-foreground hover:text-destructive"
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
