"use client";

import {
	Download,
	FileText,
	Filter,
	Loader2,
	Package,
	Plus,
	Settings2,
	Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { generateReport, generateReportBundle } from "@/app/actions";
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
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

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

export function ReportsManager() {
	const [selectedType, setSelectedType] = useState<number>(0);
	const [title, setTitle] = useState("");
	const [teamFilter, setTeamFilter] = useState("");
	const [isGenerating, setIsGenerating] = useState(false);
	const [htmlContent, setHtmlContent] = useState<string | null>(null);
	const [showHtmlDialog, setShowHtmlDialog] = useState(false);
	const [isBundling, setIsBundling] = useState(false);
	const [customPack, setCustomPack] = useState<CustomPackItem[]>([]);
	const [zebraStriping, setZebraStriping] = useState(false);

	const addToPack = () => {
		const newItem: CustomPackItem = {
			id: Math.random().toString(36).substr(2, 9),
			type: selectedType,
			title:
				title || reportTypes.find((r) => r.id === selectedType)?.name || "",
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

	const updatePackItem = (id: string, updates: Partial<CustomPackItem>) => {
		setCustomPack(
			customPack.map((item) =>
				item.id === id ? { ...item, ...updates } : item,
			),
		);
	};

	const generateCustomPack = async () => {
		if (customPack.length === 0) {
			toast.error("Pack is empty");
			return;
		}
		setIsBundling(true);
		try {
			const result = await generateReportBundle(customPack, "custom_pack.zip");
			if (result.success && result.zipContent) {
				const blob = new Blob([new Uint8Array(result.zipContent)], {
					type: "application/zip",
				});
				const url = URL.createObjectURL(blob);
				const a = document.createElement("a");
				a.href = url;
				a.download = result.filename || "custom_pack.zip";
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				URL.revokeObjectURL(url);
				toast.success("Custom pack generated successfully");
			}
		} catch (error: unknown) {
			console.error("Failed to generate custom pack", error);
			toast.error("Custom pack generation failed");
		} finally {
			setIsBundling(false);
		}
	};

	const reportPresets = [
		{
			id: "default_pack",
			name: "Default Meet Pack",
			description:
				"Complete set: Lineups, Coaches, Posting & Computer programs.",
			reports: [
				// Coaches Program
				{
					type: 4,
					title: "Coaches Meet Program",
					columnsOnPage: 2,
					showRelaySwimmers: true,
				},
				// Posting Programs
				{
					type: 4,
					title: "Posting Program - Girls",
					genderFilter: "Girls",
					columnsOnPage: 2,
					showRelaySwimmers: true,
				},
				{
					type: 4,
					title: "Posting Program - Boys",
					genderFilter: "Boys",
					columnsOnPage: 2,
					showRelaySwimmers: true,
				},
				// Computer Program
				{
					type: 4,
					title: "Computer Team Program",
					columnsOnPage: 1,
					showRelaySwimmers: true,
				},
				// Lineups (using current filters)
				...["Girls", "Boys"].flatMap((gender) =>
					["6 & under", "7-8", "9-10"].map((age) => ({
						type: 2,
						title: `Line Up - ${gender} ${age}`,
						genderFilter: gender,
						ageGroupFilter: age,
						teamFilter: teamFilter,
					})),
				),
			],
		},
		{
			id: "coaches",
			name: "Coaches Bundle",
			description: "Full meet program for all genders/ages (2-column).",
			reports: [
				{
					type: 4,
					title: `Coaches Meet Program ${new Date().toLocaleTimeString()}`,
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
					title: `Compact Meet Program ${new Date().toLocaleTimeString()}`,
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
					teamFilter: teamFilter, // Uses the team filter from config
				})),
			),
		},
	];

	const handleGenerateBundle = async (preset: (typeof reportPresets)[0]) => {
		setIsBundling(true);
		try {
			const result = await generateReportBundle(
				preset.reports,
				`${preset.name.toLowerCase().replace(/\s+/g, "_")}.zip`,
			);

			if (result.success && result.zipContent) {
				const blob = new Blob([new Uint8Array(result.zipContent)], {
					type: "application/zip",
				});
				const url = URL.createObjectURL(blob);
				const a = document.createElement("a");
				a.href = url;
				a.download = result.filename || `${preset.id}_bundle.zip`;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				URL.revokeObjectURL(url);
				toast.success(`${preset.name} generated successfully`);
			}
		} catch (error: unknown) {
			console.error("Failed to generate bundle", error);
			toast.error("Bundle generation failed");
		} finally {
			setIsBundling(false);
		}
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
			);

			if (result.success) {
				if (selectedType === 5 && result.htmlContent) {
					setHtmlContent(result.htmlContent);
					setShowHtmlDialog(true);
				} else if (result.pdfContent) {
					// Create a blob from the content
					const blob = new Blob([new Uint8Array(result.pdfContent)], {
						type: "application/pdf",
					});
					const url = URL.createObjectURL(blob);

					// Create a temporary link and click it to download
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
			}
		} catch (error: unknown) {
			console.error("Failed to generate report", error);
			const msg = error instanceof Error ? error.message : "Unknown error";
			toast.error(`Generation failed: ${msg}`);
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
						<div className="flex items-center gap-2">
							<Package className="h-5 w-5 text-primary" />
							<CardTitle>Report Presets</CardTitle>
						</div>
						<CardDescription>
							Generate pre-configured bundles for meet day
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-4">
						{reportPresets.map((preset) => (
							<div
								key={preset.id}
								className="flex items-center justify-between p-4 border rounded-lg bg-muted/10"
							>
								<div>
									<h4 className="font-medium">{preset.name}</h4>
									<p className="text-xs text-muted-foreground">
										{preset.description}
									</p>
								</div>
								<Button
									variant="outline"
									size="sm"
									onClick={() => handleGenerateBundle(preset)}
									disabled={isBundling}
								>
									{isBundling ? (
										<Loader2 className="h-4 w-4 animate-spin" />
									) : (
										"Generate"
									)}
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
								<Input
									id="team"
									placeholder="All Teams"
									value={teamFilter}
									onChange={(e) => setTeamFilter(e.target.value)}
								/>
								<Button variant="outline" size="icon">
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
							className="flex-1"
							variant="outline"
							size="lg"
							onClick={addToPack}
						>
							<Plus className="mr-2 h-4 w-4" />
							Add to Pack
						</Button>
						<Button
							className="flex-1"
							size="lg"
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
									{selectedType === 5
										? "Generate & View HTML"
										: "Generate & Download Report"}
								</>
							)}
						</Button>
					</CardFooter>
				</Card>
			</div>

			<Card className="shadow-lg border-primary/20">
				<CardHeader className="bg-primary/5">
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
						<div className="flex items-center gap-4">
							<div className="text-right">
								<p className="text-sm font-medium">
									{customPack.length} Reports Selected
								</p>
								<p className="text-xs text-muted-foreground">
									Will be delivered as a single ZIP file
								</p>
							</div>
							<Button
								onClick={generateCustomPack}
								disabled={isBundling || customPack.length === 0}
								size="lg"
							>
								{isBundling ? (
									<Loader2 className="mr-2 h-4 w-4 animate-spin" />
								) : (
									<Download className="mr-2 h-4 w-4" />
								)}
								Generate Bundle ZIP
							</Button>
						</div>
					</div>
				</CardHeader>
				<CardContent className="p-0">
					<ScrollArea className="h-[400px]">
						{customPack.length === 0 ? (
							<div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground gap-4">
								<Package className="h-12 w-12 opacity-20" />
								<p>
									Your pack is empty. Use "Add to Pack" above to get started.
								</p>
							</div>
						) : (
							<div className="divide-y">
								{customPack.map((item, index) => (
									<div
										key={item.id}
										className="p-6 hover:bg-muted/50 transition-colors"
									>
										<div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
											<div className="md:col-span-1 flex items-center justify-center">
												<div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
													{index + 1}
												</div>
											</div>
											<div className="md:col-span-10 grid grid-cols-1 md:grid-cols-3 gap-4">
												<div className="space-y-2">
													<Label className="text-xs">Report Type</Label>
													<Select
														value={item.type.toString()}
														onValueChange={(v) =>
															updatePackItem(item.id, {
																type: Number.parseInt(v, 10),
															})
														}
													>
														<SelectTrigger>
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
													<Label className="text-xs">Custom Title</Label>
													<Input
														value={item.title}
														onChange={(e) =>
															updatePackItem(item.id, { title: e.target.value })
														}
														placeholder="Report Title"
													/>
												</div>
												<div className="space-y-2">
													<Label className="text-xs">Team Filter</Label>
													<Input
														value={item.teamFilter}
														onChange={(e) =>
															updatePackItem(item.id, {
																teamFilter: e.target.value,
															})
														}
														placeholder="All Teams"
													/>
												</div>
												<div className="space-y-2">
													<Label className="text-xs">Gender</Label>
													<Select
														value={item.genderFilter}
														onValueChange={(v) =>
															updatePackItem(item.id, { genderFilter: v })
														}
													>
														<SelectTrigger>
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
													<Label className="text-xs">Age Group</Label>
													<Select
														value={item.ageGroupFilter}
														onValueChange={(v) =>
															updatePackItem(item.id, { ageGroupFilter: v })
														}
													>
														<SelectTrigger>
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
												<div className="flex items-center gap-3 pt-4">
													<Switch
														id={`zebra-${item.id}`}
														checked={item.zebraStriping}
														onCheckedChange={(v) =>
															updatePackItem(item.id, { zebraStriping: v })
														}
													/>
													<Label
														htmlFor={`zebra-${item.id}`}
														className="text-xs"
													>
														Zebra Striping
													</Label>
												</div>
											</div>
											<div className="md:col-span-1 flex justify-end pt-6">
												<Button
													variant="ghost"
													size="icon"
													className="text-destructive hover:text-destructive hover:bg-destructive/10"
													onClick={() => removeFromPack(item.id)}
												>
													<Trash2 className="h-5 w-5" />
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

			<Dialog open={showHtmlDialog} onOpenChange={setShowHtmlDialog}>
				<DialogContent className="max-w-5xl h-[90vh] flex flex-col p-0">
					<DialogHeader className="p-4 border-b">
						<DialogTitle>Meet Program Preview</DialogTitle>
					</DialogHeader>
					<div className="flex-1 w-full overflow-hidden">
						{htmlContent && (
							<iframe
								srcDoc={htmlContent}
								title="Meet Program Preview"
								className="w-full h-full border-none"
							/>
						)}
					</div>
				</DialogContent>
			</Dialog>
		</div>
	);
}
