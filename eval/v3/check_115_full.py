"""Check all §115 moments and their full content."""

import json
from pathlib import Path

data = [json.loads(l) for l in Path("../../analysis_layer/json/kuntalaki_410-2015.jsonl").read_text(encoding="utf-8").strip().split("\n")]

print("=== §115 Moments - Full Content ===\n")
for r in data:
    if r["section_id"] == "115":
        print(f"§{r['section_id']}:{r['moment']} - {r['section_title']}")
        print(f"Full text:\n{r['text']}")
        print("\n" + "="*80 + "\n")

