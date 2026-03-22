import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

fixture_path = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "anonymized_meets", "sample_data_champs_2025-aftermeet.json")
with open(fixture_path) as f:
    table_data_raw = json.load(f)
    if "data" in table_data_raw:
        table_data = table_data_raw["data"]
    else:
        table_data = table_data_raw

print(f"Raw table data size: {len(json.dumps(table_data)) / 1024 / 1024:.2f} MB")
print("Converting data once...")
t_conv0 = time.time()
converter = MmToJsonConverter(table_data=table_data)
full_data = converter.convert()
print(f"Conversion took {time.time() - t_conv0:.2f}s")
print(f"Full data size: {len(json.dumps(full_data)) / 1024 / 1024:.2f} MB")

import msgpack
import tempfile

def msgpack_encode(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj

print("Testing msgpack serialization...")
t_pack0 = time.time()
with tempfile.NamedTemporaryFile(suffix=".msgpack", delete=False) as tmp:
    tmp_path = tmp.name
    msgpack.pack({"full_data": full_data, "cache": table_data}, tmp, default=msgpack_encode)
print(f"Msgpack serialization took {time.time() - t_pack0:.4f}s")

t_unpack0 = time.time()
with open(tmp_path, "rb") as f:
    unpacked = msgpack.unpack(f, raw=False)
print(f"Msgpack deserialization took {time.time() - t_unpack0:.4f}s")
os.remove(tmp_path)

# Extract once (this is where color maps and lookup maps are built)
t_ext0 = time.time()
extractor = ReportDataExtractor(converter, full_data=full_data)
print(f"Extractor initialization took {time.time() - t_ext0:.2f}s")

start = time.time()
print("Generating 5 Meet Programs...")
for i in range(5):
    t0 = time.time()
    prog_data = extractor.extract_meet_program_data(report_title=f"Program {i}")
    renderer = WeasyRenderer(f"prog_{i}.pdf")
    renderer.render_meet_program(prog_data)
    print(f"  Program {i} took {time.time() - t0:.2f}s")
print(f"Total time (including conversion): {time.time() - t_conv0:.2f}s")
print(f"Total time (rendering only): {time.time() - start:.2f}s")
