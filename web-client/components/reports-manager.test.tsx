import {
	fireEvent,
	render,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
	generateReportBundle,
	getJobStatus,
	resolveBundleUrl,
} from "@/app/actions";
import { downloadFile } from "@/lib/tauri-bridge";
import { ReportsManager } from "./reports-manager";

// Mock server actions
vi.mock("@/app/actions", () => ({
	generateReport: vi.fn(),
	generateReportBundle: vi.fn(),
	getJobStatus: vi.fn(),
	resolveBundleUrl: vi.fn((url: string) => Promise.resolve(url)),
	getTeams: vi.fn(() => Promise.resolve({ teams: [] })),
	getDashboardStats: vi.fn(() =>
		Promise.resolve({
			totalAthletes: 10,
			totalTeams: 2,
			totalEvents: 5,
			totalResults: 0,
		}),
	),
	getDisqualifications: vi.fn(() => Promise.resolve({ disqualifications: [] })),
}));

vi.mock("@/lib/tauri-bridge", () => ({
	downloadFile: vi.fn(() => Promise.resolve()),
}));

const mockTeams = [
	{ id: "1", name: "Sharks" },
	{ id: "2", name: "Dolphins" },
];

describe("ReportsManager", () => {
	it("renders report types and presets", () => {
		render(<ReportsManager initialTeams={mockTeams} />);

		// Check some report types (use getAllByText as it might appear in summary too)
		expect(screen.getAllByText("Psych Sheet").length).toBeGreaterThan(0);
		expect(screen.getAllByText("Meet Program (PDF)").length).toBeGreaterThan(0);

		// Check presets
		expect(screen.getByText("Default Meet Pack")).toBeDefined();
		expect(screen.getAllByText("Lineup Sheets").length).toBeGreaterThan(0);
	});

	it("adds a report to the custom pack", async () => {
		render(<ReportsManager initialTeams={mockTeams} />);

		// Select a report type first
		const psychCard = screen.getByTestId("report-card-psych-sheet");
		fireEvent.click(psychCard);

		const addButton = screen.getByRole("button", { name: /Add to Pack/i });
		fireEvent.click(addButton);

		// Custom Report Pack Builder should show 1 report
		expect(screen.getByText(/1 Reports/i)).toBeDefined();

		// The builder card should contain the "Psych Sheet" input
		const builderCard = screen.getByTestId("report-builder-card");
		expect(within(builderCard).getByDisplayValue("Psych Sheet")).toBeDefined();
	});

	it("applies a preset to the builder", () => {
		// Mock scrollIntoView
		window.HTMLElement.prototype.scrollIntoView = vi.fn();

		render(<ReportsManager initialTeams={mockTeams} />);

		// Find the Lineup Sheets preset apply button
		// It has data-testid="preset-apply-lineups"
		const applyBtn = screen.getByTestId("preset-apply-lineups");
		fireEvent.click(applyBtn);

		// Check if reports were added (Lineup Sheets adds 1)
		expect(screen.getByText(/1 Reports/i)).toBeDefined();
	});

	it("generates a report bundle synchronously without polling GetJobStatus", async () => {
		vi.mocked(generateReportBundle).mockResolvedValueOnce({
			success: true,
			message: "Complete",
			jobId: "sync-job-1",
			filename: "sync_bundle.zip",
			bundleUrl: "http://localhost:3100/api/data?path=sync_bundle.zip",
			googleSheetUrls: [],
		});

		render(<ReportsManager initialTeams={mockTeams} />);

		const psychCard = screen.getByTestId("report-card-psych-sheet");
		fireEvent.click(psychCard);
		fireEvent.click(screen.getByRole("button", { name: /Add to Pack/i }));

		const generateBundleBtn = screen.getByTestId("generate-bundle-button");
		fireEvent.click(generateBundleBtn);

		await waitFor(() => {
			expect(generateReportBundle).toHaveBeenCalledTimes(1);
			expect(resolveBundleUrl).toHaveBeenCalledWith(
				"http://localhost:3100/api/data?path=sync_bundle.zip",
			);
			expect(downloadFile).toHaveBeenCalledWith(
				"sync_bundle.zip",
				"http://localhost:3100/api/data?path=sync_bundle.zip",
			);
		});
		expect(getJobStatus).not.toHaveBeenCalled();
	});
});
