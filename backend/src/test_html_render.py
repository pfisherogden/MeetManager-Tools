import os
import sys
import json

sys.path.append(os.path.dirname(__file__))
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

with open("../tests/fixtures/anonymized_champs.json") as f:
    table_data = json.load(f)

converter = MmToJsonConverter(table_data=table_data)
extractor = ReportDataExtractor(converter)

os.makedirs("../repro_reports", exist_ok=True)

# Meet Program
prog_data = extractor.extract_meet_program_data(report_title="Full Meet Program - Visual Test")
renderer = WeasyRenderer("../repro_reports/visual_full_program.html")
html = renderer.render_to_html(prog_data)
with open("../repro_reports/visual_full_program.html", "w") as f:
    f.write(html)

# Filtered Program
target = "Blue Dolphins"
filtered_prog = extractor.extract_meet_program_data(team_filter=target, report_title=f"Program - {target}")
renderer = WeasyRenderer("../repro_reports/visual_filtered_program.html")
html = renderer.render_to_html(filtered_prog)
with open("../repro_reports/visual_filtered_program.html", "w") as f:
    f.write(html)

# Psych Sheet
psych_data = extractor.extract_psych_sheet_data(report_title="Psych Sheet - Visual Test")
renderer = WeasyRenderer("../repro_reports/visual_psych_sheet.html")
html = renderer.render_to_html(psych_data, "psych_sheet.j2")
with open("../repro_reports/visual_psych_sheet.html", "w") as f:
    f.write(html)

print("HTML generation complete.")
