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
	clearAllDatasets,
	clearDataset,
	listDatasets,
	publishMeetData,
	setActiveDataset,
	uploadDataset,
	uploadDatasetFromDrive,
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
import { Input } from "@/components/ui/input";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import {
	type GoogleDriveFile,
	useGooglePicker,
} from "@/hooks/use-google-picker";
import { handleActionError } from "@/lib/error-handler";

interface Dataset {
	filename: string;
	isActive: boolean;
	lastModified?: string;
}

export function DatasetManager() {
	const [datasets, setDatasets] = useState<Dataset[]>([]);
	const [loading, setLoading] = useState(true);
	const [uploading, setUploading] = useState(false);
	const [publishing, setPublishing] = useState(false);
	const [judgeAppUrl, setJudgeAppUrl] = useState<string | null>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const { googleAccessToken } = useAuth();

	const fetchDatasets = useCallback(async () => {
		try {
			setLoading(true);
			const res: any = await listDatasets();
			if (res?.datasets) {
				setDatasets(res.datasets);
			}
		} catch (error) {
			handleActionError(error, "Failed to load datasets");
		} finally {
			setLoading(false);
		}
	}, []);

	const onDriveFileSelect = useCallback(
		async (file: GoogleDriveFile) => {
			const ext = file.name.split(".").pop()?.toLowerCase();
			if (ext !== "mdb" && ext !== "json") {
				toast.error("Invalid file type. Please select an .mdb or .json file.");
				return;
			}

			setUploading(true);
			try {
				await uploadDatasetFromDrive(file.id, file.name);
				toast.success(`Successfully imported ${file.name} from Drive`);
				fetchDatasets();
			} catch (error: unknown) {
				handleActionError(error, "Drive import failed");
			} finally {
				setUploading(false);
			}
		},
		[fetchDatasets],
	);

	const { openPicker, isLoaded: isDriveLoaded } = useGooglePicker({
		onFileSelect: onDriveFileSelect,
		accessToken: googleAccessToken,
	});

	useEffect(() => {
		fetchDatasets();
	}, [fetchDatasets]);

	const handleSetActive = async (filename: string) => {
		try {
			await setActiveDataset(filename);
			toast.success(`Active dataset changed to ${filename}`);
			fetchDatasets();
		} catch (error) {
			handleActionError(error, "Failed to set active dataset");
		}
	};

	const handlePublish = async () => {
		setPublishing(true);
		try {
			// Pass the current origin to ensure the backend generates correct production links
			const origin =
				typeof window !== "undefined" ? window.location.origin : undefined;
			const res = await publishMeetData(origin);
			if (res.success) {
				setJudgeAppUrl(res.judgeAppUrl);
				toast.success("Meet data published for Judge App");
			}
		} catch (error: unknown) {
			handleActionError(error, "Failed to publish");
		} finally {
			setPublishing(false);
		}
	};

	const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) return;

		const ext = file.name.split(".").pop()?.toLowerCase();
		if (ext !== "mdb" && ext !== "json") {
			toast.error("Invalid file type. Please upload an .mdb or .json file.");
			return;
		}

		const formData = new FormData();
		formData.append("file", file);

		setUploading(true);
		try {
			await uploadDataset(formData);
			toast.success("Dataset uploaded successfully");
			if (fileInputRef.current) fileInputRef.current.value = "";
			fetchDatasets();
		} catch (error: unknown) {
			handleActionError(error, "Upload failed");
		} finally {
			setUploading(false);
		}
	};

	const handleDelete = async (filename: string) => {
		if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
		try {
			await clearDataset(filename);
			toast.success(`Deleted ${filename}`);
			fetchDatasets();
		} catch (error: unknown) {
			handleActionError(error, "Failed to delete dataset");
		}
	};

	const handleClearAll = async () => {
		if (
			!confirm(
				"Are you sure you want to delete ALL datasets? This cannot be undone.",
			)
		)
			return;
		try {
			await clearAllDatasets();
			toast.success("All datasets deleted");
			fetchDatasets();
		} catch (error: unknown) {
			handleActionError(error, "Failed to clear datasets");
		}
	};

	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between">
				<div>
					<CardTitle>Dataset Management</CardTitle>
					<CardDescription>
						Upload and manage MDB database files
					</CardDescription>
				</div>
				<div className="flex items-center gap-2">
					<Input
						type="file"
						accept=".mdb,.json"
						className="hidden"
						ref={fileInputRef}
						onChange={handleUpload}
					/>
					<Button
						disabled={uploading}
						onClick={() => fileInputRef.current?.click()}
					>
						{uploading && !isDriveLoaded ? (
							<>
								<Loader2 className="mr-2 h-4 w-4 animate-spin" />
								Uploading...
							</>
						) : (
							<>
								<Upload className="mr-2 h-4 w-4" />
								Upload Dataset
							</>
						)}
					</Button>
					<Button
						variant="outline"
						onClick={openPicker}
						disabled={uploading || !isDriveLoaded}
					>
						{uploading && isDriveLoaded ? (
							<>
								<Loader2 className="mr-2 h-4 w-4 animate-spin" />
								Importing...
							</>
						) : (
							<>
								<HardDrive className="mr-2 h-4 w-4" />
								Import from Drive
							</>
						)}
					</Button>
					<Button
						variant="destructive"
						onClick={handleClearAll}
						disabled={loading || datasets.length === 0}
					>
						<Trash2 className="mr-2 h-4 w-4" />
						Clear All
					</Button>
				</div>
			</CardHeader>
			<CardContent>
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Filename</TableHead>
							<TableHead>Status</TableHead>
							<TableHead>Last Modified</TableHead>
							<TableHead className="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{loading ? (
							<TableRow>
								<TableCell colSpan={4} className="text-center py-8">
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
								<TableRow key={dataset.filename}>
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
											? (() => {
													const ts = parseFloat(dataset.lastModified);
													if (!Number.isNaN(ts) && ts > 0) {
														return formatDistanceToNow(new Date(ts * 1000), {
															addSuffix: true,
														});
													}
													return "-";
												})()
											: "-"}
									</TableCell>
									<TableCell className="text-right flex items-center justify-end gap-2">
										{dataset.isActive && (
											<Button
												variant="outline"
												size="sm"
												onClick={handlePublish}
												disabled={publishing}
												className="gap-2"
												data-testid="publish-button"
											>
												{publishing ? (
													<Loader2 className="h-4 w-4 animate-spin" />
												) : (
													<QrCode className="h-4 w-4" />
												)}
												Publish to Judge App
											</Button>
										)}
										{!dataset.isActive && (
											<Button
												variant="outline"
												size="sm"
												onClick={() => handleSetActive(dataset.filename)}
											>
												Set Active
											</Button>
										)}
										<Button
											variant="ghost"
											size="icon"
											className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
											onClick={() => handleDelete(dataset.filename)}
										>
											<Trash2 className="h-4 w-4" />
										</Button>
									</TableCell>
								</TableRow>
							))
						)}
					</TableBody>
				</Table>
			</CardContent>

			<Dialog open={!!judgeAppUrl} onOpenChange={() => setJudgeAppUrl(null)}>
				<DialogContent className="sm:max-w-md">
					<DialogHeader>
						<DialogTitle>Judge App Setup</DialogTitle>
						<DialogDescription>
							Scan this QR code with a mobile device to load the meet data into
							the Stroke and Turn Judge App.
						</DialogDescription>
					</DialogHeader>
					<div className="flex flex-col items-center justify-center space-y-4 py-4">
						<div className="bg-white p-4 rounded-lg shadow-sm border">
							{judgeAppUrl && (
								<QRCodeSVG value={judgeAppUrl} size={256} level="H" />
							)}
						</div>
						<p className="text-xs text-center text-muted-foreground break-all px-4">
							{judgeAppUrl}
						</p>
						<Button asChild variant="outline" className="w-full">
							<a href={judgeAppUrl || "#"} target="_blank" rel="noreferrer">
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
