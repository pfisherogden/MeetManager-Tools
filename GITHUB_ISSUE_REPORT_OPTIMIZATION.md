# Performance Analysis & Optimization Proposals for Report Generation

## Background
Report generation currently takes minutes on Cloud Run. This analysis identifies bottlenecks in the existing **JVM/Jackcess** and **WeasyPrint** stack and proposes architectural and algorithmic optimizations to achieve faster generation without switching core technologies.

## Current Bottlenecks

### 1. Redundant Data Processing (High Impact)
In `server.py`, multiple reports are generated in parallel using `ProcessPoolExecutor` with a `spawn` context.
- **The Issue**: Each worker process re-initializes an `MmToJsonConverter` and calls `convert()`. This means for 5 reports, the system performs the same expensive O(N) table joins and denormalization logic 5 times.
- **IPC Overhead**: The raw `cache` (list of dicts) is pickled and sent to each worker. For large meets, this is a major CPU and memory hit.

### 2. Algorithmic Inefficiencies in `MmToJsonConverter`
- **Table Scans**: Methods like `add_entries_to_event` perform a linear scan of the entry DataFrame/Table for *every* event. 
- **Jackcess Row Conversion**: `_read_table_jackcess` iterates through every row and column, performing type-checking and manual conversion to Python dicts.

### 3. JVM Startup & Initialization
While `JPype` keeps the JVM alive in the main process, workers in a `spawn` context start fresh.
- **The Issue**: If workers touch the MDB directly, they incur JVM startup costs.

---

## Proposed Optimizations (Preserving Existing Stack)

### Phase 1: Architecture & IPC (High Reward)

#### P1.1: "Single Conversion" Workflow
Modify the report generation flow to perform `MmToJsonConverter.convert()` **once** in the main process. 
- Result: A single, fully denormalized "Meet Object" (the data expected by `ReportDataExtractor`).
- Advantage: Eliminates redundant O(N) work in workers.

#### P1.2: MessagePack Serialized IPC via `/tmp`
Instead of pickling large dictionaries:
1. Serialize the denormalized meet data to a binary format like **MessagePack** (faster than JSON/Pickle).
2. Store it in `/tmp/meet_data.msgpack` (which is in-memory `tmpfs` on Cloud Run).
3. Pass only the filename to workers. Workers load the pre-denormalized data in milliseconds.

### Phase 2: Algorithmic Tuning (Medium Complexity)

#### P2.1: Pre-Calculated Indexing (GroupBy)
Replace linear table scans with dictionary lookups or Pandas `groupby`.
```python
# Optimize MmToJsonConverter.add_entries_to_event
# Instead of df[df['event_ptr'] == event.event_ptr] in a loop:
grouped = df.groupby('event_ptr')
# ... entries = grouped.get_group(event.event_ptr)
```

#### P2.2: Optimize Jackcess Object Conversion
Refactor `_read_table_jackcess` to pre-calculate column types and names once per table, avoiding repeated string operations and `type()` checks in the inner loop.

#### P2.3: Subset font loading in WeasyPrint
Modify `WeasyRenderer` to use a persistent `FontConfiguration` passed from the main process if possible, or ensure it's pre-warmed.

### Phase 3: WeasyPrint Rendering Performance

#### P3.1: HTML Structure Simplification
Audit Jinja2 templates (`meet_program.j2`) to reduce deep nesting and complex CSS rules (e.g., `nth-child` over large tables). Simpler HTML leads to faster layout calculations in `WeasyPrint`.

#### P3.2: Parallel Page Processing (Experimental)
If documents are very large, consider generating HTML for separate sessions in parallel, rendering them to separate PDFs, and merging them using `pypdf`.

---

## Verification Plan
1. **Profiling**: Use `cProfile` and `line_profiler` on `MmToJsonConverter.convert` to confirm the exact cost of row-by-row conversion.
2. **Benchmark**: Use the existing `Sample_Data.json` (scaled up 10x) to measure the impact of the Single Conversion strategy.
3. **Memory Audit**: Monitor memory usage on Cloud Run during parallel generation to ensure `/tmp` usage doesn't trigger OOM.
