"use client";

import { Download, FileText, Filter, Loader2, Settings2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { generateReport } from "@/app/actions";
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

export function ReportsManager() {
	const [selectedType, setSelectedType] = useState<number>(0);
	const [title, setTitle] = useState("");
	const [teamFilter, setTeamFilter] = useState("");
	const [isGenerating, setIsGenerating] = useState(false);
	const [htmlContent, setHtmlContent] = useState<string | null>(null);
	const [showHtmlDialog, setShowHtmlDialog] = useState(false);

	const handleGenerate = async () => {
		setIsGenerating(true);
		try {
			const reportName =
				reportTypes.find((r) => r.id === selectedType)?.name || "Report";
			const result = await generateReport(
				selectedType,
				title || reportName,
				teamFilter,
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

			<Card className="max-w-2xl mx-auto shadow-lg">
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
								<span className="text-muted-foreground">Branding:</span> No Meet
								Manager headers/footers
							</p>
						</div>
					</div>
				</CardContent>
				<CardFooter className="bg-muted/10 border-t pt-6">
					<Button
						className="w-full"
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
