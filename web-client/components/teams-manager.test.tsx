import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Team } from "@/lib/swim-meet-types";
import { TeamsManager } from "./teams-manager";

const mockTeams: Team[] = [
	{
		id: "t1",
		name: "Sharks",
		abbreviation: "SHK",
		city: "San Jose",
		state: "CA",
		athleteCount: 45,
		color: "#FF0000",
	},
	{
		id: "t2",
		name: "Dolphins",
		abbreviation: "DOL",
		city: "Palo Alto",
		state: "CA",
		athleteCount: 38,
		color: "#0000FF",
	},
];

describe("TeamsManager", () => {
	it("renders teams table with data", () => {
		render(<TeamsManager initialTeams={mockTeams} />);

		expect(screen.getByText("Sharks")).toBeDefined();
		expect(screen.getByText("Dolphins")).toBeDefined();
		expect(screen.getByText("SHK")).toBeDefined();
		expect(screen.getByText("DOL")).toBeDefined();
		expect(screen.getByText("45")).toBeDefined();
		expect(screen.getByText("38")).toBeDefined();
	});
});
