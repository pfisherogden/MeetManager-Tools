import time
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

start = time.time()
print("Generating 5 Meet Programs...")
for i in range(5):
    t0 = time.time()
    prog_data = extractor.extract_meet_program_data(report_title=f"Program {i}")
    renderer = WeasyRenderer(f"prog_{i}.pdf")
    renderer.render_meet_program(prog_data)
    print(f"  Program {i} took {time.time() - t0:.2f}s")
print(f"Total time: {time.time() - start:.2f}s")
