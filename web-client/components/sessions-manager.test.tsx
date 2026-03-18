import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Session } from "@/lib/swim-meet-types";
import { SessionsManager } from "./sessions-manager";

const mockSessions: Session[] = [
	{
		id: "s1",
		name: "Saturday Morning",
		meetId: "m1",
		date: "2024-06-22",
		warmUpTime: "7:00 AM",
		startTime: "8:30 AM",
		eventCount: 45,
	},
	{
		id: "s2",
		name: "Sunday Afternoon",
		meetId: "m1",
		date: "2024-06-23",
		warmUpTime: "12:00 PM",
		startTime: "1:30 PM",
		eventCount: 38,
	},
];

const mockMeets = [{ id: "m1", name: "Summer Champs" }];

describe("SessionsManager", () => {
	it("renders sessions table with data", () => {
		render(<SessionsManager initialSessions={mockSessions} meets={mockMeets} />);

		expect(screen.getByText("Saturday Morning")).toBeDefined();
		expect(screen.getByText("Sunday Afternoon")).toBeDefined();
		expect(screen.getAllByText("Summer Champs")).toBeDefined();
		expect(screen.getByText("7:00 AM")).toBeDefined();
		expect(screen.getByText("8:30 AM")).toBeDefined();
		expect(screen.getByText("45")).toBeDefined();
		expect(screen.getByText("38")).toBeDefined();
	});
});
