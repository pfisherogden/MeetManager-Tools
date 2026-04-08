import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Relay } from "@/lib/swim-meet-types";
import { RelaysManager } from "./relays-manager";

// Mock next/navigation
const mockGet = vi.fn();
vi.mock("next/navigation", () => ({
	useSearchParams: () => ({
		get: mockGet,
	}),
}));

const mockRelays: Relay[] = [
	{
		id: "r1",
		eventId: "e1",
		teamId: "t1",
		teamName: "Team A",
		leg1: "Swimmer 1",
		leg2: "Swimmer 2",
		leg3: "Swimmer 3",
		leg4: "Swimmer 4",
		seedTime: "2:00.00",
		finalTime: "1:59.50",
		place: 1,
	},
	{
		id: "r2",
		eventId: "e2",
		teamId: "t2",
		teamName: "Team B",
		leg1: "Swimmer 5",
		leg2: "Swimmer 6",
		leg3: "Swimmer 7",
		leg4: "Swimmer 8",
		seedTime: "2:10.00",
		finalTime: null,
		place: null,
	},
];

describe("RelaysManager", () => {
	it("renders relays table with data", () => {
		render(<RelaysManager initialRelays={mockRelays} />);

		expect(screen.getByText("Team A")).toBeDefined();
		expect(screen.getByText("Team B")).toBeDefined();
		expect(screen.getByText("Swimmer 1")).toBeDefined();
		expect(screen.getByText("Swimmer 8")).toBeDefined();
		expect(screen.getByText("2:00.00")).toBeDefined();
	});

	it("filters relays based on event search param", () => {
		mockGet.mockReturnValue("e1");

		render(<RelaysManager initialRelays={mockRelays} />);

		expect(screen.getByText("Team A")).toBeDefined();
		expect(screen.queryByText("Team B")).toBeNull();
	});
});
