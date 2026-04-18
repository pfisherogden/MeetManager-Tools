# Skill: Visual Regression Testing for PDF Reports

Use this skill when modifying PDF templates (`.j2`), CSS (`report_style.css`), or reporting logic (`extractor.py`).

## **Core Principle**
Never claim a layout is "fixed" or "optimized" without empirical evidence using large datasets and AI-assisted visual comparison.

## **Step 1: Baseline Generation ("Before")**
1.  **Select Dataset**: Always use a large championship-scale dataset (e.g., `tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json`).
2.  **Generate Baseline**: Run a repro script (e.g., `repro_report_size.py`) inside the Docker container to capture the current state.
    ```bash
    docker cp repro_report_size.py meetmanager-tools-backend-1:/app/
    docker compose exec backend python /app/repro_report_size.py
    docker cp meetmanager-tools-backend-1:/app/test_meet_program.pdf large_before_program.pdf
    ```

## **Step 2: Iterative Fixing ("After")**
1.  **Apply Changes**: Use the CSS Table model (`display: table`) for layout stability.
2.  **Regenerate**: 
    ```bash
    docker compose exec backend python /app/repro_report_size.py
    docker cp meetmanager-tools-backend-1:/app/test_meet_program.pdf large_after_program.pdf
    ```

## **Step 3: AI-Assisted Analysis**
Invoke the `generalist` sub-agent to find regressions that human eyes might miss.

**Analysis Prompt Template:**
> Please analyze the differences between `large_before_X.pdf` and `large_after_X.pdf`. 
> 1. Check vertical alignment of headers ("Lane", "Name", etc.) with data rows.
> 2. Check for "gutter bleed" (content extending into center margins).
> 3. Check relay swimmer numbering (1, 2, 3, 4) alignment.
> 4. Check for DQ line overflow or wrapping.

## **Step 4: Benchmarking**
Measure the impact on rendering time. 
*   **Target**: CSS Table Layout should be ~40% faster than Flexbox.
*   **Verification**: Run a timing-loop benchmark script with 3+ iterations.

## **Red Flags**
- **Flexbox in PDF**: WeasyPrint's flex engine is slow and prone to drifting. Use tables.
- **Small Dataset Success**: Small datasets (8 pages) often hide alignment issues that only appear on page 20+.
- **Manual "Eyeballing"**: Always use the AI to verify mathematical alignment.
