import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DatasetManager } from "./dataset-manager";

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
	uploadDatasetFromDrive: vi.fn(),
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
vi.mock("@/hooks/use-google-picker", () => ({
	useGooglePicker: vi.fn(() => ({
		openPicker: vi.fn(),
		isLoaded: true,
	})),
}));

describe("DatasetManager", () => {
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
	});
});
