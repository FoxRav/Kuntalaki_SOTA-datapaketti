"""Show remaining failures."""
import json
from pathlib import Path

results = json.loads(Path("kuntalaki_eval_v3_results.json").read_text(encoding="utf-8"))

print("=== REMAINING FAILURES ===\n")
for r in results["results"]:
    if not r["passed"]:
        hits_info = ""
        if r["hits"]:
            top = r["hits"][0]
            hits_info = f"Top-1: {top['section_num']}:{top['moment']} score={top['score']:.4f}"
        print(f"{r['id']} [{r['category']}]")
        print(f"  Query: {r['query'][:60]}...")
        print(f"  Expected: {r['expected_any']}")
        print(f"  {hits_info}")
        print()

