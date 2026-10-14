import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listDatasets, uploadDatasetFromDrive } from "@/app/actions";
import {
	type GoogleDriveFile,
	useGooglePicker,
} from "@/hooks/use-google-picker";
import { DatasetManager } from "./dataset-manager";

// Mock sonner toast
vi.mock("sonner", () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}));

// Mock next/navigation
const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
	useRouter: () => ({
		refresh: mockRefresh,
		push: vi.fn(),
	}),
}));

// Mock server actions
vi.mock("@/app/actions", () => ({
	listDatasets: vi.fn(() =>
		Promise.resolve({
			datasets: [
				{ filename: "meet1.mdb", isActive: true, lastModified: "1710720000" },
				{ filename: "meet2.mdb", isActive: false, lastModified: "1710633600" },
			],
		}),
	),
	setActiveDataset: vi.fn(),
	uploadDataset: vi.fn(),
	uploadDatasetFromDrive: vi.fn(() =>
		Promise.resolve({ success: true, message: "Saved" }),
	),
	deleteDataset: vi.fn(),
	clearDataset: vi.fn(),
	clearAllDatasets: vi.fn(),
	publishMeetData: vi.fn(),
}));

// Mock useAuth
vi.mock("@/hooks/use-auth", () => ({
	useAuth: vi.fn(() => ({
		user: { uid: "test-user" },
		googleAccessToken: "test-token",
		loading: false,
	})),
}));

// Mock useGooglePicker
const mockOpenPicker = vi.fn();
let capturedOnFileSelect: ((file: GoogleDriveFile) => Promise<void>) | null =
	null;

vi.mock("@/hooks/use-google-picker", () => ({
	useGooglePicker: vi.fn(({ onFileSelect }) => {
		capturedOnFileSelect = onFileSelect;
		return {
			openPicker: mockOpenPicker,
			isLoaded: true,
		};
	}),
}));

describe("DatasetManager", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		capturedOnFileSelect = null;
	});

	it("renders dataset table with data after loading", async () => {
		render(<DatasetManager />);

		// Initially shows loading
		expect(screen.getByRole("status")).toBeDefined();

		// Wait for data to load
		await waitFor(() => {
			expect(screen.getByText("meet1.mdb")).toBeDefined();
			expect(screen.getByText("meet2.mdb")).toBeDefined();
		});

		expect(screen.getByText("Active")).toBeDefined();
		expect(screen.getByText("Set Active")).toBeDefined();
		expect(screen.getByTestId("import-from-drive-button")).toBeDefined();
	});

	it("opens Google Picker when clicking Import from Drive", async () => {
		render(<DatasetManager />);

		await waitFor(() => {
			expect(screen.getByText("meet1.mdb")).toBeDefined();
		});

		const importBtn = screen.getByTestId("import-from-drive-button");
		fireEvent.click(importBtn);
		expect(mockOpenPicker).toHaveBeenCalledTimes(1);
		expect(useGooglePicker).toHaveBeenCalled();
	});

	it("imports .mdb, .json, and .zip files selected from Google Drive", async () => {
		render(<DatasetManager />);

		await waitFor(() => {
			expect(screen.getByText("meet1.mdb")).toBeDefined();
		});

		expect(capturedOnFileSelect).not.toBeNull();

		// Test .mdb import
		await capturedOnFileSelect!({
			id: "drive-file-123",
			name: "Champs2026.mdb",
			mimeType: "application/x-msaccess",
			sizeBytes: 1024,
			accessToken: "picker-oauth-token",
			contentBase64: "dGVzdC1tZGItY29udGVudA==",
		});

		expect(uploadDatasetFromDrive).toHaveBeenCalledWith(
			"drive-file-123",
			"Champs2026.mdb",
			"picker-oauth-token",
			"dGVzdC1tZGItY29udGVudA==",
		);
		expect(toast.success).toHaveBeenCalledWith(
			"Successfully imported Champs2026.mdb from Drive",
		);
		expect(mockRefresh).toHaveBeenCalled();
		expect(listDatasets).toHaveBeenCalledTimes(2);

		// Test .zip import
		await capturedOnFileSelect!({
			id: "drive-zip-456",
			name: "Swmm7Bkup.zip",
			mimeType: "application/zip",
			sizeBytes: 2048,
		});

		expect(uploadDatasetFromDrive).toHaveBeenCalledWith(
			"drive-zip-456",
			"Swmm7Bkup.zip",
			"test-token",
			undefined,
		);
	});

	it("rejects unsupported file extensions from Google Drive", async () => {
		render(<DatasetManager />);

		await waitFor(() => {
			expect(screen.getByText("meet1.mdb")).toBeDefined();
		});

		await capturedOnFileSelect!({
			id: "drive-bad-1",
			name: "notes.txt",
			mimeType: "text/plain",
			sizeBytes: 100,
		});

		expect(uploadDatasetFromDrive).not.toHaveBeenCalled();
		expect(toast.error).toHaveBeenCalledWith(
			"Invalid file type. Please select an .mdb, .json, or .zip file.",
		);
	});

	it("displays error toast when Drive import fails", async () => {
		vi.mocked(uploadDatasetFromDrive).mockResolvedValueOnce({
			success: false,
			message: "Drive quota exceeded",
		});

		render(<DatasetManager />);

		await waitFor(() => {
			expect(screen.getByText("meet1.mdb")).toBeDefined();
		});

		await capturedOnFileSelect!({
			id: "drive-fail-1",
			name: "fail.json",
			mimeType: "application/json",
			sizeBytes: 512,
		});

		expect(toast.error).toHaveBeenCalledWith("Drive quota exceeded");
	});
});
