import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Athlete } from "@/lib/swim-meet-types";
import { AthletesManager } from "./athletes-manager";

const mockAthletes: Athlete[] = [
	{
		id: "1",
		firstName: "Michael",
		lastName: "Phelps",
		teamId: "t1",
		teamName: "USA",
		dateOfBirth: "1985-06-30",
		gender: "M",
		age: 38,
	},
	{
		id: "2",
		firstName: "Katie",
		lastName: "Ledecky",
		teamId: "t1",
		teamName: "USA",
		dateOfBirth: "1997-03-17",
		gender: "F",
		age: 26,
	},
];

const mockTeams = ["USA", "Other"];

describe("AthletesManager", () => {
	it("renders athletes table with data", () => {
		render(
			<AthletesManager initialAthletes={mockAthletes} teams={mockTeams} />,
		);

		expect(screen.getByText("Michael")).toBeDefined();
		expect(screen.getByText("Phelps")).toBeDefined();
		expect(screen.getByText("Katie")).toBeDefined();
		expect(screen.getByText("Ledecky")).toBeDefined();
		expect(screen.getAllByText("USA")).toBeDefined();
	});

	it("renders gender labels correctly", () => {
		render(
			<AthletesManager initialAthletes={mockAthletes} teams={mockTeams} />,
		);

		expect(screen.getByText("Male")).toBeDefined();
		expect(screen.getByText("Female")).toBeDefined();
	});
});
