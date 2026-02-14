"use client";

import {
	Check,
	ChevronDown,
	ChevronUp,
	Edit2,
	Plus,
	Trash2,
	X,
} from "lucide-react";
import type * as React from "react";
import { useCallback, useMemo, useState } from "react";
import { DataTableFacetedFilter } from "@/components/data-table-faceted-filter";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface Column<T> {
	key: keyof T;
	label: string;
	width?: string;
	editable?: boolean;
	type?: "text" | "number" | "select" | "date";
	filterVariant?: "text" | "faceted";
	options?: string[];
	render?: (value: T[keyof T], row: T) => React.ReactNode;
}

interface DataTableProps<T extends { id: string }> {
	data: T[];
	columns: Column<T>[];
	onAdd?: () => void;
	onDelete?: (id: string) => void;
	onUpdate?: (id: string, key: keyof T, value: T[keyof T]) => void;
	title?: string;
}

export function DataTable<T extends { id: string }>({
	data,
	columns,
	onAdd,
	onDelete,
	onUpdate,
	title,
}: DataTableProps<T>) {
	const [sortKey, setSortKey] = useState<keyof T | null>(null);
	const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

	// Per-column filter state.
	// For text filters, value is a string.
	// For faceted filters, value is a Set<string>.
	const [filters, setFilters] = useState<Record<string, string | Set<string>>>(
		{},
	);

	const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
	const [editingCell, setEditingCell] = useState<{
		id: string;
		key: keyof T;
	} | null>(null);
	const [editValue, setEditValue] = useState<string>("");

	const handleSort = useCallback(
		(key: keyof T) => {
			if (sortKey === key) {
				setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
			} else {
				setSortKey(key);
				setSortDirection("asc");
			}
		},
		[sortKey],
	);

	const handleFilterChange = (key: keyof T, value: string | Set<string>) => {
		setFilters((prev) => ({
			...prev,
			[key as string]: value,
		}));
	};

	const handleSelectAll = useCallback(() => {
		if (selectedRows.size === data.length) {
			setSelectedRows(new Set());
		} else {
			setSelectedRows(new Set(data.map((row) => row.id)));
		}
	}, [data, selectedRows.size]);

	const handleSelectRow = useCallback((id: string) => {
		setSelectedRows((prev) => {
			const next = new Set(prev);
			if (next.has(id)) {
				next.delete(id);
			} else {
				next.add(id);
			}
			return next;
		});
	}, []);

	const startEditing = useCallback(
		(id: string, key: keyof T, currentValue: T[keyof T]) => {
			setEditingCell({ id, key });
			setEditValue(String(currentValue ?? ""));
		},
		[],
	);

	const saveEdit = useCallback(() => {
		if (editingCell && onUpdate) {
			onUpdate(editingCell.id, editingCell.key, editValue as T[keyof T]);
		}
		setEditingCell(null);
		setEditValue("");
	}, [editingCell, editValue, onUpdate]);

	const cancelEdit = useCallback(() => {
		setEditingCell(null);
		setEditValue("");
	}, []);

	// Auto-generate options for faceted filters if not provided, based on current data
	const facetedOptions = useMemo(() => {
		const optionsMap: Record<string, { label: string; value: string }[]> = {};

		columns.forEach((col) => {
			if (col.filterVariant === "faceted") {
				if (col.options) {
					optionsMap[String(col.key)] = col.options.map((o) => ({
						label: o,
						value: o,
					}));
				} else {
					// Derive from data
					const uniqueValues = Array.from(
						new Set(data.map((row) => String(row[col.key] ?? ""))),
					)
						.filter(Boolean)
						.sort();
					optionsMap[String(col.key)] = uniqueValues.map((v) => ({
						label: v,
						value: v,
					}));
				}
			}
		});
		return optionsMap;
	}, [data, columns]);

	const filteredData = useMemo(() => {
		let result = [...data];

		// Apply per-column filters (AND logic)
		// We only care about filters that are "active" (non-empty string or non-empty Set)
		const activeFilters = Object.entries(filters).filter(([_, val]) => {
			if (val instanceof Set) return val.size > 0;
			return typeof val === "string" && val.trim() !== "";
		});

		if (activeFilters.length > 0) {
			result = result.filter((row) => {
				return activeFilters.every(([key, filterVal]) => {
					const rowVal = String(row[key as keyof T] ?? "");

					if (filterVal instanceof Set) {
						// Faceted match: must be one of the selected values
						const val = String(rowVal ?? "").trim();
						if (!val) return false;
						return filterVal.has(val);
					} else {
						// Text match: substring, case-insensitive
						return rowVal
							.toLowerCase()
							.includes((filterVal as string).toLowerCase());
					}
				});
			});
		}

		// Sorting
		if (sortKey) {
			result.sort((a, b) => {
				const aVal = a[sortKey];
				const bVal = b[sortKey];

				// Handle undefined/null
				if (aVal == null && bVal == null) return 0;
				if (aVal == null) return sortDirection === "asc" ? 1 : -1;
				if (bVal == null) return sortDirection === "asc" ? -1 : 1;

				// Numeric sort if possible
				const aNum = Number(aVal);
				const bNum = Number(bVal);
				if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
					return sortDirection === "asc" ? aNum - bNum : bNum - aNum;
				}

				const comparison = String(aVal).localeCompare(String(bVal), undefined, {
					numeric: true,
				});
				return sortDirection === "asc" ? comparison : -comparison;
			});
		}

		return result;
	}, [data, filters, sortKey, sortDirection]);

	return (
		<div className="flex flex-col h-full">
			{/* Toolbar */}
			<div className="flex items-center justify-between gap-4 p-4 border-b border-border bg-card">
				<div className="flex items-center gap-3">
					{title && (
						<h2 className="text-lg font-semibold text-foreground">{title}</h2>
					)}
					<span className="text-sm text-muted-foreground">
						{filteredData.length}{" "}
						{filteredData.length === 1 ? "record" : "records"}
					</span>
				</div>
				<div className="flex items-center gap-2">
					{/* Global search removed in favor of column filters */}
					{onAdd && (
						<Button
							onClick={onAdd}
							size="sm"
							className="bg-primary hover:bg-primary/90"
						>
							<Plus className="h-4 w-4 mr-1" />
							Add
						</Button>
					)}
					{selectedRows.size > 0 && onDelete && (
						<Button
							onClick={() => {
								selectedRows.forEach((id) => {
									onDelete(id);
								});
								setSelectedRows(new Set());
							}}
							size="sm"
							variant="destructive"
						>
							<Trash2 className="h-4 w-4 mr-1" />
							Delete ({selectedRows.size})
						</Button>
					)}
				</div>
			</div>

			{/* Table */}
			<div className="flex-1 overflow-auto">
				<table className="w-full border-collapse">
					<thead className="sticky top-0 z-10">
						<tr className="bg-muted/70 backdrop-blur-sm">
							<th className="w-10 p-0 align-bottom border-b border-r border-border">
								<div className="flex items-center justify-center h-full pb-2">
									<input
										type="checkbox"
										checked={
											selectedRows.size === data.length && data.length > 0
										}
										onChange={handleSelectAll}
										className="h-4 w-4 rounded border-border accent-primary"
									/>
								</div>
							</th>
							{columns.map((col) => (
								<th
									key={String(col.key)}
									className={cn(
										"text-left p-2 border-b border-r border-border last:border-r-0 align-top",
										col.width,
									)}
								>
									<div className="flex flex-col gap-2">
										<button
											type="button"
											onClick={() => handleSort(col.key)}
											className="flex items-center gap-1 w-full text-sm font-medium text-foreground hover:text-primary transition-colors"
										>
											{col.label}
											{sortKey === col.key &&
												(sortDirection === "asc" ? (
													<ChevronUp className="h-3 w-3" />
												) : (
													<ChevronDown className="h-3 w-3" />
												))}
										</button>

										<div className="relative">
											{col.filterVariant === "faceted" ? (
												<DataTableFacetedFilter
													title={col.label}
													options={facetedOptions[String(col.key)] || []}
													selectedValues={
														(filters[String(col.key)] as Set<string>) ||
														new Set()
													}
													onSelect={(newValues) =>
														handleFilterChange(col.key, newValues)
													}
												/>
											) : (
												<div className="relative">
													<Input
														placeholder="Filter..."
														className="h-7 text-[10px] italic text-muted-foreground bg-background/50 px-2"
														value={(filters[String(col.key)] as string) || ""}
														onChange={(e) =>
															handleFilterChange(col.key, e.target.value)
														}
													/>
													{filters[String(col.key)] && (
														<button
															type="button"
															onClick={() => handleFilterChange(col.key, "")}
															className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
														>
															<X className="h-3 w-3" />
														</button>
													)}
												</div>
											)}
										</div>
									</div>
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{filteredData.map((row, rowIndex) => (
							<tr
								key={row.id}
								className={cn(
									"group",
									selectedRows.has(row.id) && "bg-primary/5",
									rowIndex % 2 === 0 ? "bg-card" : "bg-muted/20",
								)}
							>
								<td className="w-10 p-0 border-b border-r border-border">
									<div className="flex items-center justify-center h-10">
										<input
											type="checkbox"
											checked={selectedRows.has(row.id)}
											onChange={() => handleSelectRow(row.id)}
											className="h-4 w-4 rounded border-border accent-primary"
										/>
									</div>
								</td>
								{columns.map((col) => {
									const isEditing =
										editingCell?.id === row.id && editingCell?.key === col.key;
									const value = row[col.key];

									return (
										<td
											key={String(col.key)}
											className={cn(
												"p-0 border-b border-r border-border last:border-r-0",
												col.width,
											)}
										>
											{isEditing ? (
												<div className="flex items-center h-10 px-1 gap-1">
													{col.type === "select" && col.options ? (
														<DropdownMenu>
															<DropdownMenuTrigger asChild>
																<Button
																	variant="outline"
																	size="sm"
																	className="h-8 w-full justify-start bg-transparent"
																>
																	{editValue}
																	<ChevronDown className="h-4 w-4 ml-auto" />
																</Button>
															</DropdownMenuTrigger>
															<DropdownMenuContent>
																{col.options.map((opt) => (
																	<DropdownMenuItem
																		key={opt}
																		onClick={() => setEditValue(opt)}
																	>
																		{opt}
																	</DropdownMenuItem>
																))}
															</DropdownMenuContent>
														</DropdownMenu>
													) : (
														<Input
															value={editValue}
															onChange={(e) => setEditValue(e.target.value)}
															onKeyDown={(e) => {
																if (e.key === "Enter") saveEdit();
																if (e.key === "Escape") cancelEdit();
															}}
															type={
																col.type === "number"
																	? "number"
																	: col.type === "date"
																		? "date"
																		: "text"
															}
															className="h-8 text-sm"
															autoFocus
														/>
													)}
													<Button
														size="sm"
														variant="ghost"
														className="h-8 w-8 p-0"
														onClick={saveEdit}
													>
														<Check className="h-4 w-4 text-green-600" />
													</Button>
													<Button
														size="sm"
														variant="ghost"
														className="h-8 w-8 p-0"
														onClick={cancelEdit}
													>
														<X className="h-4 w-4 text-destructive" />
													</Button>
												</div>
											) : (
												// biome-ignore lint/a11y/noStaticElementInteractions: Cell interaction requires complex keyboard support not interpreted by linter
												<div
													className={cn(
														"flex items-center h-10 px-3 text-sm",
														col.editable &&
														onUpdate &&
														"cursor-pointer hover:bg-primary/5 group/cell",
													)}
													onDoubleClick={() => {
														if (col.editable && onUpdate) {
															startEditing(row.id, col.key, value);
														}
													}}
												>
													<span className="truncate flex-1">
														{col.render
															? col.render(value, row)
															: String(value ?? "")}
													</span>
													{col.editable && onUpdate && (
														<Edit2 className="h-3 w-3 text-muted-foreground opacity-0 group-hover/cell:opacity-100 transition-opacity ml-2" />
													)}
												</div>
											)}
										</td>
									);
								})}
							</tr>
						))}
						{filteredData.length === 0 && (
							<tr>
								<td
									colSpan={columns.length + 1}
									className="h-32 text-center text-muted-foreground"
								>
									{Object.keys(filters).length > 0
										? "No results found matching filters"
										: "No data available"}
								</td>
							</tr>
						)}
					</tbody>
				</table>
			</div>
		</div>
	);
}
