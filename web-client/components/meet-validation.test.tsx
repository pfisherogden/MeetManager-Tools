import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MeetValidation } from "./meet-validation";

// Mock the validateActiveMeet action
vi.mock("@/app/actions", () => ({
	validateActiveMeet: vi.fn(() =>
		Promise.resolve({
			success: true,
			message: "Validation completed with 3 findings.",
			findings: [
				{
					severity: 3,
					category: "Rules Limit",
					message: "Swimmer A exceeds limits",
					affectedId: "101",
				},
				{
					severity: 2,
					category: "0 Backup Timers",
					message: "Swimmer B has 0 backup timers",
					affectedId: "102",
				},
				{
					severity: 1,
					category: "0 Backup Timers",
					message: "Swimmer C has 0 backup timers",
					affectedId: "103",
				},
			],
		}),
	),
}));

describe("MeetValidation", () => {
	it("renders title and run check button", () => {
		render(<MeetValidation />);
		expect(screen.getByText("Meet Rules & Data Validation")).toBeDefined();
		expect(screen.getByText("Run Validation Check")).toBeDefined();
	});

	it("runs validation and displays findings with category and severity filters", async () => {
		render(<MeetValidation />);
		const runBtn = screen.getByText("Run Validation Check");
		fireEvent.click(runBtn);

		await waitFor(() => {
			expect(
				screen.getByText("Validation completed with 3 findings."),
			).toBeDefined();
		});

		// Verify category counts are displayed
		expect(screen.getAllByText("Rules Limit").length).toBeGreaterThanOrEqual(1);
		expect(
			screen.getAllByText("0 Backup Timers").length,
		).toBeGreaterThanOrEqual(1);

		// Verify severity badges/checkbox text are displayed
		expect(screen.getByText("Critical (1)")).toBeDefined();
		expect(screen.getByText("Warning (1)")).toBeDefined();
		expect(screen.getByText("Info (1)")).toBeDefined();

		// Verify finding details are displayed
		expect(screen.getByText("Swimmer A exceeds limits")).toBeDefined();
		expect(
			screen.getAllByText("Swimmer B has 0 backup timers").length,
		).toBeGreaterThanOrEqual(1);
		expect(
			screen.getAllByText("Swimmer C has 0 backup timers").length,
		).toBeGreaterThanOrEqual(1);
	});
});
