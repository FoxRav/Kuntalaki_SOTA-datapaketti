"""Check §115 content and tags."""

import json
from pathlib import Path

data = [json.loads(l) for l in Path("../../analysis_layer/json/kuntalaki_410-2015.jsonl").read_text(encoding="utf-8").strip().split("\n")]

print("=== §115 Moments ===\n")
for r in data:
    if r["section_id"] == "115":
        print(f"§{r['section_id']}:{r['moment']} - {r['section_title']}")
        print(f"Tags: {r['tags']}")
        print(f"Text: {r['text'][:300]}...")
        print()

