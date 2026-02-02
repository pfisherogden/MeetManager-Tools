"use client"

import * as React from "react"
import { useState, useCallback } from "react"
import { ChevronDown, ChevronUp, Plus, Trash2, Search, X, Check, Edit2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export interface Column<T> {
  key: keyof T
  label: string
  width?: string
  editable?: boolean
  type?: 'text' | 'number' | 'select' | 'date'
  options?: string[]
  render?: (value: T[keyof T], row: T) => React.ReactNode
}

interface DataTableProps<T extends { id: string }> {
  data: T[]
  columns: Column<T>[]
  onAdd?: () => void
  onDelete?: (id: string) => void
  onUpdate?: (id: string, key: keyof T, value: T[keyof T]) => void
  title?: string
}

export function DataTable<T extends { id: string }>({
  data,
  columns,
  onAdd,
  onDelete,
  onUpdate,
  title,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<keyof T | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
  const [editingCell, setEditingCell] = useState<{ id: string; key: keyof T } | null>(null)
  const [editValue, setEditValue] = useState<string>('')

  const handleSort = useCallback((key: keyof T) => {
    if (sortKey === key) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }, [sortKey])

  const handleSelectAll = useCallback(() => {
    if (selectedRows.size === data.length) {
      setSelectedRows(new Set())
    } else {
      setSelectedRows(new Set(data.map(row => row.id)))
    }
  }, [data, selectedRows.size])

  const handleSelectRow = useCallback((id: string) => {
    setSelectedRows(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const startEditing = useCallback((id: string, key: keyof T, currentValue: T[keyof T]) => {
    setEditingCell({ id, key })
    setEditValue(String(currentValue ?? ''))
  }, [])

  const saveEdit = useCallback(() => {
    if (editingCell && onUpdate) {
      onUpdate(editingCell.id, editingCell.key, editValue as T[keyof T])
    }
    setEditingCell(null)
    setEditValue('')
  }, [editingCell, editValue, onUpdate])

  const cancelEdit = useCallback(() => {
    setEditingCell(null)
    setEditValue('')
  }, [])

  const filteredData = React.useMemo(() => {
    let result = [...data]
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(row => 
        columns.some(col => {
          const value = row[col.key]
          return String(value).toLowerCase().includes(query)
        })
      )
    }
    
    if (sortKey) {
      result.sort((a, b) => {
        const aVal = a[sortKey]
        const bVal = b[sortKey]
        const comparison = String(aVal).localeCompare(String(bVal), undefined, { numeric: true })
        return sortDirection === 'asc' ? comparison : -comparison
      })
    }
    
    return result
  }, [data, searchQuery, sortKey, sortDirection, columns])

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          {title && <h2 className="text-lg font-semibold text-foreground">{title}</h2>}
          <span className="text-sm text-muted-foreground">
            {filteredData.length} {filteredData.length === 1 ? 'record' : 'records'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 w-64 h-9 bg-muted/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          {onAdd && (
            <Button onClick={onAdd} size="sm" className="bg-primary hover:bg-primary/90">
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          )}
          {selectedRows.size > 0 && onDelete && (
            <Button
              onClick={() => {
                selectedRows.forEach(id => onDelete(id))
                setSelectedRows(new Set())
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
              <th className="w-10 p-0">
                <div className="flex items-center justify-center h-10 border-b border-r border-border">
                  <input
                    type="checkbox"
                    checked={selectedRows.size === data.length && data.length > 0}
                    onChange={handleSelectAll}
                    className="h-4 w-4 rounded border-border accent-primary"
                  />
                </div>
              </th>
              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  className={cn(
                    "text-left p-0 border-b border-r border-border last:border-r-0",
                    col.width
                  )}
                >
                  <button
                    onClick={() => handleSort(col.key)}
                    className="flex items-center gap-1 w-full h-10 px-3 text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
                  >
                    {col.label}
                    {sortKey === col.key && (
                      sortDirection === 'asc' 
                        ? <ChevronUp className="h-4 w-4 text-primary" />
                        : <ChevronDown className="h-4 w-4 text-primary" />
                    )}
                  </button>
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
                  rowIndex % 2 === 0 ? "bg-card" : "bg-muted/20"
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
                  const isEditing = editingCell?.id === row.id && editingCell?.key === col.key
                  const value = row[col.key]
                  
                  return (
                    <td
                      key={String(col.key)}
                      className={cn(
                        "p-0 border-b border-r border-border last:border-r-0",
                        col.width
                      )}
                    >
                      {isEditing ? (
                        <div className="flex items-center h-10 px-1 gap-1">
                          {col.type === 'select' && col.options ? (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="outline" size="sm" className="h-8 w-full justify-start bg-transparent">
                                  {editValue}
                                  <ChevronDown className="h-4 w-4 ml-auto" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent>
                                {col.options.map(opt => (
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
                                if (e.key === 'Enter') saveEdit()
                                if (e.key === 'Escape') cancelEdit()
                              }}
                              type={col.type === 'number' ? 'number' : col.type === 'date' ? 'date' : 'text'}
                              className="h-8 text-sm"
                              autoFocus
                            />
                          )}
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={saveEdit}>
                            <Check className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={cancelEdit}>
                            <X className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      ) : (
                        <div
                          className={cn(
                            "flex items-center h-10 px-3 text-sm",
                            col.editable && onUpdate && "cursor-pointer hover:bg-primary/5 group/cell"
                          )}
                          onDoubleClick={() => {
                            if (col.editable && onUpdate) {
                              startEditing(row.id, col.key, value)
                            }
                          }}
                        >
                          <span className="truncate flex-1">
                            {col.render ? col.render(value, row) : String(value ?? '')}
                          </span>
                          {col.editable && onUpdate && (
                            <Edit2 className="h-3 w-3 text-muted-foreground opacity-0 group-hover/cell:opacity-100 transition-opacity ml-2" />
                          )}
                        </div>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
            {filteredData.length === 0 && (
              <tr>
                <td 
                  colSpan={columns.length + 1} 
                  className="h-32 text-center text-muted-foreground"
                >
                  {searchQuery ? 'No results found' : 'No data available'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
