import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { type Column, DataTable } from "./data-table";

interface TestData {
	id: string;
	name: string;
	age: number;
}

const mockData: TestData[] = [
	{ id: "1", name: "Alice", age: 30 },
	{ id: "2", name: "Bob", age: 25 },
	{ id: "3", name: "Charlie", age: 35 },
];

const mockColumns: Column<TestData>[] = [
	{ key: "name", label: "Name", filterVariant: "text" },
	{ key: "age", label: "Age", type: "number" },
];

describe("DataTable", () => {
	it("renders table with data", () => {
		render(<DataTable data={mockData} columns={mockColumns} />);

		expect(screen.getByText("Alice")).toBeDefined();
		expect(screen.getByText("Bob")).toBeDefined();
		expect(screen.getByText("Charlie")).toBeDefined();
		expect(screen.getByText("3 records")).toBeDefined();
	});

	it("sorts data when clicking header", () => {
		render(<DataTable data={mockData} columns={mockColumns} />);

		const nameHeader = screen.getByText("Name");

		// Initial order: Alice, Bob, Charlie
		let rows = screen.getAllByRole("row").slice(1); // skip header row
		expect(rows[0].textContent).toContain("Alice");

		// Click to sort (already asc by default usually or first click is asc)
		fireEvent.click(nameHeader);

		// Click again for desc
		fireEvent.click(nameHeader);
		rows = screen.getAllByRole("row").slice(1);
		expect(rows[0].textContent).toContain("Charlie");
	});

	it("filters data using text input", () => {
		render(<DataTable data={mockData} columns={mockColumns} />);

		const filterInput = screen.getAllByPlaceholderText("Filter...")[0];
		fireEvent.change(filterInput, { target: { value: "Alice" } });

		expect(screen.getByText("Alice")).toBeDefined();
		expect(screen.queryByText("Bob")).toBeNull();
		expect(screen.getByText("1 record")).toBeDefined();
	});

	it("handles row selection", () => {
		const onDelete = vi.fn();
		render(
			<DataTable data={mockData} columns={mockColumns} onDelete={onDelete} />,
		);

		const checkboxes = screen.getAllByRole("checkbox");
		const firstRow = checkboxes[1];

		fireEvent.click(firstRow);
		// Should show delete button with count
		expect(screen.getByText(/Delete \(1\)/i)).toBeDefined();
	});

	it("renders empty state when no data", () => {
		render(<DataTable data={[]} columns={mockColumns} />);
		expect(screen.getByText("No data available")).toBeDefined();
	});
});
