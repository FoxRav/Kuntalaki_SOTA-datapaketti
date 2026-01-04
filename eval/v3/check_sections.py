"""Check specific section content."""

import json
from pathlib import Path

data = [json.loads(l) for l in Path("../../analysis_layer/json/kuntalaki_410-2015.jsonl").read_text(encoding="utf-8").strip().split("\n")]

sections_to_check = ["148", "113"]

for sec in sections_to_check:
    print(f"=== {sec} ===\n")
    for r in data:
        if r["section_id"] == sec:
            print(f"{sec}:{r['moment']} - {r['section_title']}")
            print(f"Text: {r['text'][:200]}...")
            print()

