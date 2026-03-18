import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Meet } from "@/lib/swim-meet-types";
import { MeetsManager } from "./meets-manager";

const mockMeets: Meet[] = [
	{
		id: "m1",
		name: "Winter Invitational",
		location: "Aquatic Center",
		startDate: "2024-01-15",
		endDate: "2024-01-17",
		poolType: "SCY",
		status: "active",
	},
	{
		id: "m2",
		name: "Summer Champs",
		location: "Olympic Pool",
		startDate: "2024-07-10",
		endDate: "2024-07-14",
		poolType: "LCM",
		status: "upcoming",
	},
];

describe("MeetsManager", () => {
	it("renders meets table with data", () => {
		render(<MeetsManager initialMeets={mockMeets} />);

		expect(screen.getByText("Winter Invitational")).toBeDefined();
		expect(screen.getByText("Summer Champs")).toBeDefined();
		expect(screen.getByText("Aquatic Center")).toBeDefined();
		expect(screen.getByText("Olympic Pool")).toBeDefined();
		expect(screen.getByText("SCY")).toBeDefined();
		expect(screen.getByText("LCM")).toBeDefined();
	});

	it("renders status badges correctly", () => {
		render(<MeetsManager initialMeets={mockMeets} />);

		expect(screen.getByText("active")).toBeDefined();
		expect(screen.getByText("upcoming")).toBeDefined();
	});
});
