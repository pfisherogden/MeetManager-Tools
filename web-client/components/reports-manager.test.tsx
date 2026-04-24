import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReportsManager } from "./reports-manager";

// Mock server actions
vi.mock("@/app/actions", () => ({
	generateReport: vi.fn(),
	generateReportBundle: vi.fn(),
	getJobStatus: vi.fn(),
	getTeams: vi.fn(() => Promise.resolve({ teams: [] })),
	getDashboardStats: vi.fn(() =>
		Promise.resolve({
			totalAthletes: 10,
			totalTeams: 2,
			totalEvents: 5,
			totalResults: 0,
		}),
	),
}));

const _mockTeams = [
	{ id: "t1", name: "Sharks", code: "SHK", athleteCount: 45 },
	{ id: "t2", name: "Dolphins", code: "DOL", athleteCount: 38 },
];

describe("ReportsManager", () => {
	it("renders report types and presets", () => {
		render(<ReportsManager />);
		expect(screen.getByText(/Report Presets/i)).toBeDefined();

		// Use testId for specificity to avoid ambiguous text matches
		expect(screen.getByTestId("report-card-psych-sheet")).toBeDefined();
		expect(screen.getByTestId("report-card-meet-entries")).toBeDefined();
	});

	it("adds a report to the custom pack", () => {
		render(<ReportsManager />);

		// 1. Select a report type card to reveal the configuration card
		const reportCard = screen.getByTestId("report-card-psych-sheet");
		fireEvent.click(reportCard);

		// 2. Click "Add to Pack" - find button specifically to avoid text ambiguity
		const configCard = screen.getByTestId("report-configuration-card");
		const addBtn = within(configCard).getByRole("button", {
			name: /Add to Pack/i,
		});
		fireEvent.click(addBtn);

		// 3. Verify it appears in the builder (look for specific summary text)
		const builder =
			screen.getByTestId("generate-bundle-button").closest(".card") ||
			document.body;
		expect(within(builder).getByText(/1 Reports/i)).toBeDefined();
	});

	it("applies a preset to the builder", () => {
		render(<ReportsManager />);

		const applyBtn = screen.getByTestId("preset-apply-lineups");
		fireEvent.click(applyBtn);

		// Check if multiple reports were added (Lineup Sheets adds many)
		const builderHeader = screen.getByText(/Reports in custom pack/i);
		expect(builderHeader.textContent).toContain("12");
	});
});
