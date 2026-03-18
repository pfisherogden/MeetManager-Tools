import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Dashboard } from "./dashboard";

// Mock useConfig
vi.mock("@/components/config-provider", () => ({
	useConfig: () => ({
		meetName: "Test Championship",
	}),
}));

const mockStats = {
	meetCount: 1,
	teamCount: 5,
	athleteCount: 120,
	eventCount: 45,
};

describe("Dashboard", () => {
	it("renders stats correctly", () => {
		render(<Dashboard stats={mockStats} />);

		expect(screen.getByText("Total Meets")).toBeDefined();
		expect(screen.getByText("1")).toBeDefined();
		
		expect(screen.getByText("Teams")).toBeDefined();
		expect(screen.getByText("5")).toBeDefined();
		
		expect(screen.getByText("Athletes")).toBeDefined();
		expect(screen.getByText("120")).toBeDefined();
		
		expect(screen.getByText("Events")).toBeDefined();
		expect(screen.getByText("45")).toBeDefined();
	});

	it("renders meet name from config", () => {
		render(<Dashboard stats={mockStats} />);
		expect(screen.getByText("Test Championship")).toBeDefined();
	});
});
