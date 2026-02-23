import json
import os
import sys

repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(repo_root, 'backend', 'src'))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.judge_app_extractor import JudgeAppExtractor

fixture_path = os.path.join(repo_root, "tests/fixtures/anonymized_meets/sample_data_champs_2025-aftermeet.json")
with open(fixture_path, 'r') as f:
    payload = json.load(f)
    table_data = payload.get("data", payload)

converter = MmToJsonConverter(table_data=table_data)
extractor = JudgeAppExtractor(converter)
judge_data = extractor.extract_judge_data()

out_path = os.path.join(repo_root, "mobile-judge-app/assets/sample_program.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as f:
    json.dump(judge_data, f, indent=2)

print(f"Wrote {len(judge_data['events'])} events to {out_path}")
