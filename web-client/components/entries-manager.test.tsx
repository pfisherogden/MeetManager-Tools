import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { EntriesManager } from "./entries-manager";
import type { Entry } from "@/lib/swim-meet-types";

// Mock next/navigation
const mockGet = vi.fn();
vi.mock("next/navigation", () => ({
    useSearchParams: () => ({
        get: mockGet,
    }),
}));

const mockEntries: Entry[] = [
    {
        id: "1",
        athleteId: "a1",
        athleteName: "John Doe",
        eventId: "e1",
        eventName: "100 Free",
        teamId: "t1",
        teamName: "Sharks",
        seedTime: "1:00.00",
        finalTime: "1:00.10",
        place: 1,
        heat: 1,
        lane: 4,
    },
    {
        id: "2",
        athleteId: "a2",
        athleteName: "Jane Smith",
        eventId: "e2",
        eventName: "200 IM",
        teamId: "t2",
        teamName: "Dolphins",
        seedTime: "2:30.00",
        finalTime: null,
        place: null,
        heat: 2,
        lane: 3,
    },
];

describe("EntriesManager", () => {
    it("renders entries table with data", () => {
        render(<EntriesManager initialEntries={mockEntries} />);

        expect(screen.getByText("John Doe")).toBeDefined();
        expect(screen.getByText("Jane Smith")).toBeDefined();
        expect(screen.getByText("Sharks")).toBeDefined();
        expect(screen.getByText("Dolphins")).toBeDefined();
        expect(screen.getByText("100 Free")).toBeDefined();
        expect(screen.getByText("1:00.00")).toBeDefined();
    });

    it("filters entries based on event search param", () => {
        mockGet.mockReturnValue("e1");

        render(<EntriesManager initialEntries={mockEntries} />);

        expect(screen.getByText("John Doe")).toBeDefined();
        expect(screen.queryByText("Jane Smith")).toBeNull();
    });
});
