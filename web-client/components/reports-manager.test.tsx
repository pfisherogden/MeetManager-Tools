import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReportsManager } from "./reports-manager";

// Mock server actions
vi.mock("@/app/actions", () => ({
	generateReport: vi.fn(),
	generateReportBundle: vi.fn(),
	getJobStatus: vi.fn(),
	getTeams: vi.fn(() => Promise.resolve({ teams: [] })),
}));

const _mockTeams = [
	{ id: "t1", name: "Sharks", code: "SHK", athleteCount: 45 },
	{ id: "t2", name: "Dolphins", code: "DOL", athleteCount: 38 },
];

describe("ReportsManager", () => {
	it("renders report types and presets", () => {
		render(<ReportsManager />);
		expect(screen.getByText(/Report Presets/i)).toBeDefined();
		expect(screen.getByText(/Psych Sheet/i)).toBeDefined();
		expect(screen.getByText(/Meet Entries/i)).toBeDefined();
	});

	it("adds a report to the custom pack", () => {
		render(<ReportsManager />);

		// 1. Select a report type card to reveal the configuration card
		const reportCard = screen.getByTestId("report-card-psych-sheet");
		fireEvent.click(reportCard);

		// 2. Click "Add to Pack"
		const addBtn = screen.getByText(/Add to Pack/i);
		fireEvent.click(addBtn);

		// 3. Verify it appears in the builder
		expect(screen.getByText(/1 Reports/i)).toBeDefined();
	});

	it("applies a preset to the builder", () => {
		render(<ReportsManager />);

		const applyBtn = screen.getByTestId("preset-apply-lineups");
		fireEvent.click(applyBtn);

		// Check if multiple reports were added (Lineup Sheets adds many)
		expect(screen.getByText(/12 Reports/i)).toBeDefined();
	});
});
