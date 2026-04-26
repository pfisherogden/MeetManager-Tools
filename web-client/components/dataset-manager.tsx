"use client";

import { formatDistanceToNow } from "date-fns";
import {
	Check,
	Database,
	ExternalLink,
	HardDrive,
	Loader2,
	QrCode,
	Trash2,
	Upload,
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
	deleteDataset,
	listDatasets,
	publishMeetData,
	setActiveDataset,
} from "@/app/actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";

interface Dataset {
	filename: string;
	isActive: boolean;
	lastModified: string;
}

export function DatasetManager() {
	const [datasets, setDatasets] = useState<Dataset[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [isUploading, setIsUploading] = useState(false);
	const [isPublishing, setIsPublishing] = useState<string | null>(null);
	const [judgeUrl, setJudgeUrl] = useState<string | null>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const fetchDatasets = useCallback(async () => {
		try {
			const res = await listDatasets();
			setDatasets(res.datasets);
		} catch (_error) {
			toast.error("Failed to load datasets");
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchDatasets();
	}, [fetchDatasets]);

	const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) {
			console.log("E2E DEBUG: No file selected in input");
			return;
		}

		console.log(`E2E DEBUG: Uploading file: ${file.name}, size: ${file.size}`);
		setIsUploading(true);
		const formData = new FormData();
		formData.append("file", file);

		try {
			// Manual upload implementation using a server action
			const { uploadDataset } = await import("@/app/actions");
			console.log("E2E DEBUG: Calling uploadDataset server action...");
			const res = await uploadDataset(formData);

			if (res.success) {
				console.log("E2E DEBUG: Upload success!");
				toast.success("Dataset uploaded successfully");
				await fetchDatasets();
			} else {
				console.log(`E2E DEBUG: Upload failed: ${res.message}`);
				toast.error(res.message || "Upload failed");
			}
		} catch (error) {
			console.error("E2E DEBUG: Upload error:", error);
			toast.error("An error occurred during upload");
		} finally {
			setIsUploading(false);
			if (fileInputRef.current) fileInputRef.current.value = "";
		}
	};

	const handleSetActive = async (filename: string) => {
		try {
			const res = await setActiveDataset(filename);
			if (res.success) {
				toast.success(`Active dataset set to: ${filename}`);
				// NUCLEAR: Force full page reload to ensure revalidated data is shown
				window.location.href = "/admin";
			} else {
				toast.error(res.message || "Failed to set active dataset");
			}
		} catch (_error) {
			toast.error("An error occurred");
		}
	};

	const handleDelete = async (filename: string) => {
		if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

		try {
			const res = await deleteDataset(filename);
			if (res.success) {
				toast.success("Dataset deleted");
				await fetchDatasets();
			} else {
				toast.error(res.message || "Delete failed");
			}
		} catch (_error) {
			toast.error("An error occurred");
		}
	};

	const handlePublish = async (filename: string) => {
		setIsPublishing(filename);
		try {
			const res = await publishMeetData(filename);
			if (res.success && res.judgeAppUrl) {
				setJudgeUrl(res.judgeAppUrl);
				toast.success("Meet data published to Judge App");
			} else {
				toast.error(res.message || "Publishing failed");
			}
		} catch (_error) {
			toast.error("An error occurred during publishing");
		} finally {
			setIsPublishing(null);
		}
	};

	return (
		<Card className="shadow-lg border-primary/20">
			<CardHeader className="bg-primary/5">
				<div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
					<div className="flex items-center gap-2">
						<HardDrive className="h-5 w-5 text-primary" />
						<div>
							<CardTitle>Dataset Management</CardTitle>
							<CardDescription>
								Upload and manage MeetManager .mdb (JSON-converted) files.
							</CardDescription>
						</div>
					</div>
					<div className="flex items-center gap-2">
						<input
							type="file"
							className="absolute w-px h-px opacity-0"
							ref={fileInputRef}
							onChange={handleUpload}
							accept=".json"
							data-testid="dataset-file-input"
						/>
						<Button
							onClick={() => fileInputRef.current?.click()}
							disabled={isUploading}
							className="bg-primary hover:bg-primary/90"
							data-testid="upload-dataset-button"
						>
							{isUploading ? (
								<Loader2 className="mr-2 h-4 w-4 animate-spin" />
							) : (
								<Upload className="mr-2 h-4 w-4" />
							)}
							Upload Dataset
						</Button>
					</div>
				</div>
			</CardHeader>
			<CardContent className="p-0">
				<div className="overflow-x-auto">
					<Table>
						<TableHeader>
							<TableRow className="bg-muted/50">
								<TableHead className="w-[300px]">Filename</TableHead>
								<TableHead>Status</TableHead>
								<TableHead>Last Modified</TableHead>
								<TableHead className="text-right">Actions</TableHead>
							</TableRow>
						</TableHeader>
						<TableBody>
							{isLoading ? (
								<TableRow>
									<TableCell colSpan={4} className="h-32 text-center">
										<Loader2
											role="status"
											className="h-6 w-6 animate-spin mx-auto text-muted-foreground"
										/>
									</TableCell>
								</TableRow>
							) : datasets.length === 0 ? (
								<TableRow>
									<TableCell
										colSpan={4}
										className="text-center py-8 text-muted-foreground"
									>
										No datasets found. Upload one to get started.
									</TableCell>
								</TableRow>
							) : (
								datasets.map((dataset) => (
									<TableRow
										key={dataset.filename}
										data-testid={`dataset-row-${dataset.filename}`}
										data-active={dataset.isActive}
										data-test-state={dataset.isActive ? "active" : "inactive"}
									>
										<TableCell className="font-medium flex items-center gap-2">
											<Database className="h-4 w-4 text-muted-foreground" />
											{dataset.filename}
										</TableCell>
										<TableCell>
											{dataset.isActive && (
												<Badge
													variant="secondary"
													className="gap-1 bg-green-100 text-green-800 hover:bg-green-100 uppercase text-[10px]"
													data-testid="active-dataset-badge"
												>
													<Check className="h-3 w-3" /> Active
												</Badge>
											)}
										</TableCell>
										<TableCell className="text-muted-foreground text-sm">
											{dataset.lastModified
												? formatDistanceToNow(new File([], "").lastModified, {
														addSuffix: true,
													})
												: "-"}
										</TableCell>
										<TableCell className="text-right flex items-center justify-end gap-2">
											<Button
												variant={dataset.isActive ? "secondary" : "outline"}
												size="sm"
												onClick={() => handleSetActive(dataset.filename)}
												data-testid="set-active-button"
											>
												{dataset.isActive ? "Re-activate" : "Set Active"}
											</Button>
											<Button
												variant="outline"
												size="sm"
												disabled={isPublishing === dataset.filename}
												onClick={() => handlePublish(dataset.filename)}
												data-testid="publish-button"
											>
												{isPublishing === dataset.filename ? (
													<Loader2 className="h-4 w-4 animate-spin" />
												) : (
													<QrCode className="h-4 w-4" />
												)}
												<span className="ml-2 hidden sm:inline">
													Publish to Judge App
												</span>
											</Button>
											<Button
												variant="ghost"
												size="icon"
												className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
												onClick={() => handleDelete(dataset.filename)}
												data-testid="delete-dataset-button"
											>
												<Trash2 className="h-4 w-4" />
											</Button>
										</TableCell>
									</TableRow>
								))
							)}
						</TableBody>
					</Table>
				</div>
			</CardContent>

			<Dialog open={!!judgeUrl} onOpenChange={() => setJudgeUrl(null)}>
				<DialogContent className="sm:max-w-md">
					<DialogHeader>
						<DialogTitle>Judge App Ready</DialogTitle>
						<DialogDescription>
							Scan this QR code with a mobile device to start judging this meet.
						</DialogDescription>
					</DialogHeader>
					<div className="flex flex-col items-center justify-center space-y-6 py-4">
						<div className="p-4 bg-white rounded-xl shadow-inner border">
							{judgeUrl && (
								<QRCodeSVG
									value={judgeUrl}
									size={256}
									level="H"
									includeMargin
								/>
							)}
						</div>
						<div className="text-center space-y-2">
							<p className="text-sm font-medium text-muted-foreground">
								Target URL:
							</p>
							<code
								className="px-2 py-1 bg-muted rounded text-xs break-all max-w-[300px] block"
								data-testid="judge-app-url"
							>
								{judgeUrl}
							</code>
						</div>
						<Button asChild className="w-full">
							<a href={judgeUrl || "#"} target="_blank" rel="noreferrer">
								<ExternalLink className="mr-2 h-4 w-4" />
								Open in Browser
							</a>
						</Button>
					</div>
				</DialogContent>
			</Dialog>
		</Card>
	);
}
