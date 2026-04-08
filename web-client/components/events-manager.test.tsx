import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SwimEvent } from "@/lib/swim-meet-types";
import { EventsManager } from "./events-manager";

// Mock next/navigation
const mockGet = vi.fn();
vi.mock("next/navigation", () => ({
	useSearchParams: () => ({
		get: mockGet,
	}),
}));

const mockEvents: SwimEvent[] = [
	{
		id: "e1",
		sessionId: "1",
		eventNumber: 1,
		distance: 50,
		stroke: "Freestyle",
		gender: "M",
		ageGroup: "9-10",
		entryCount: 24,
	},
	{
		id: "e2",
		sessionId: "2",
		eventNumber: 2,
		distance: 100,
		stroke: "IM",
		gender: "F",
		ageGroup: "11-12",
		entryCount: 18,
	},
];

const mockSessions = [
	{ id: "1", name: "Session 1" },
	{ id: "2", name: "Session 2" },
];

describe("EventsManager", () => {
	it("renders events table with data", () => {
		render(
			<EventsManager initialEvents={mockEvents} sessions={mockSessions} />,
		);

		expect(screen.getByText("Freestyle")).toBeDefined();
		expect(screen.getByText("IM")).toBeDefined();
		expect(screen.getByText("50")).toBeDefined();
		expect(screen.getByText("100")).toBeDefined();
		expect(screen.getByText("24")).toBeDefined();
		expect(screen.getByText("18")).toBeDefined();
	});

	it("filters events based on session search param", () => {
		mockGet.mockReturnValue("1");

		render(
			<EventsManager initialEvents={mockEvents} sessions={mockSessions} />,
		);

		expect(screen.getByText("Freestyle")).toBeDefined();
		expect(screen.queryByText("IM")).toBeNull();
	});
});
