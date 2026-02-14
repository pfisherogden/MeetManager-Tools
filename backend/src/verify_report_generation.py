import csv
import io
import os
import subprocess
import sys

# Ensure mm_to_json is in path
sys.path.append(os.path.dirname(__file__))  # Add backend/src

# Correct imports
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.config import GroupConfig, ReportConfig, ReportLayout, TextStyle
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.renderer import PDFRenderer


def load_mdb(db_path):
    print(f"Exporting tables from {db_path} using mdb-export...")
    try:
        tables = subprocess.check_output(["mdb-tables", "-1", db_path]).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error listing tables: {e}")
        return {}

    data = {}
    for t in tables:
        if not t.strip():
            continue
        try:
            # -Q prevents quoting issues sometimes, but standard CSV is better
            csv_out = subprocess.check_output(["mdb-export", db_path, t]).decode("utf-8")
            # Parse CSV to list of dicts
            data[t] = list(csv.DictReader(io.StringIO(csv_out)))
        except Exception as e:
            print(f"Skipping table {t}: {e}")
    return data


def verify_report_generation():
    # 1. Load Data
    data_path = "data/after meet - TVSL Championship Meet July 19, 2025.mdb"
    if not os.path.exists(data_path):
        # Try one level up if run from src/
        data_path = "../data/after meet - TVSL Championship Meet July 19, 2025.mdb"
        if not os.path.exists(data_path):
            print(f"Error: {data_path} not found.")
            return

    print("Loading MDB...")
    table_data = load_mdb(data_path)
    converter = MmToJsonConverter(table_data=table_data)

    # 2. Extract Data
    print("Extracting Report Data...")
    extractor = ReportDataExtractor(converter)

    # Try filtering for "Demon" team as in reference
    report_data = extractor.extract_meet_entries_data(team_filter="Demon")

    if not_data(report_data):
        print("Warning: No data for 'Demon'. Trying all teams...")
        report_data = extractor.extract_meet_entries_data(team_filter=None)

    if not_data(report_data):
        print("Error: No data extracted at all.")
        return

    # 3. Define Config
    print("Configuring Report...")
    config = ReportConfig(
        title="Entries - All Events",
        layout=ReportLayout(page_size="Letter", margin_top=0.75, margin_bottom=0.5, margin_left=0.5, margin_right=0.5),
        header_style=TextStyle(font_name="Helvetica-Bold", font_size=14, alignment=1, space_after=4),
        subheader_style=TextStyle(font_name="Helvetica", font_size=10, alignment=1, space_after=4),
        main_group=GroupConfig(
            group_by="team_name",
            header_style=TextStyle(font_name="Helvetica-Bold", font_size=12, alignment=0, space_after=6),
            page_break_after=False,
            new_page_per_group=True,
        ),
        item_group=GroupConfig(group_by="athlete_name", item_layout="2col_table"),
        two_column_layout=True,
    )

    # 4. Render PDF
    output_pdf = "data/example_reports/verification_entries_v5.pdf"
    if not os.path.exists("data/example_reports"):
        output_pdf = "../data/example_reports/verification_entries_v5.pdf"

    print(f"Rendering PDF to {output_pdf}...")
    renderer = PDFRenderer(output_pdf, config)
    renderer.render(report_data)

    # 5. Verify Additional Reports
    print("Generating Psych Sheet...")
    psych_data = extractor.extract_psych_sheet_data()
    from mm_to_json.reporting.report_definitions import PSYCH_SHEET_CONFIG

    PDFRenderer("data/example_reports/verification_psych.pdf", PSYCH_SHEET_CONFIG).render(psych_data)

    print("Generating Timer Sheets...")
    timer_data = extractor.extract_timer_sheets_data()
    from mm_to_json.reporting.report_definitions import TIMER_SHEETS_CONFIG

    PDFRenderer("data/example_reports/verification_timers.pdf", TIMER_SHEETS_CONFIG).render(timer_data)

    print("Generating Meet Results...")
    results_data = extractor.extract_results_data()
    from mm_to_json.reporting.report_definitions import RESULTS_REPORT_CONFIG

    PDFRenderer("data/example_reports/verification_results.pdf", RESULTS_REPORT_CONFIG).render(results_data)

    print("Generating Meet Program...")
    program_data = extractor.extract_meet_program_data()
    from mm_to_json.reporting.report_definitions import MEET_PROGRAM_CONFIG

    PDFRenderer("data/example_reports/verification_meet_program_v5.pdf", MEET_PROGRAM_CONFIG).render(program_data)

    print("Done!")


def not_data(data):
    if not data.get("groups"):
        return True
    return False


if __name__ == "__main__":
    verify_report_generation()
