"""Analyze MUST questions Top-1 hit rate."""

import json
from pathlib import Path

results = json.loads(Path("kuntalaki_eval_v3_results.json").read_text(encoding="utf-8"))

print("=== MUST Questions Top-1 Analysis ===\n")
must_top1_pass = 0
must_total = 0

for r in results["results"]:
    if r["must"]:
        must_total += 1
        top1_correct = r.get("top1_hit", False)
        status = "TOP-1 OK" if top1_correct else "TOP-1 MISS"
        
        if top1_correct:
            must_top1_pass += 1
        
        print(f"{r['id']}: {status}")
        if r["hits"]:
            h = r["hits"][0]
            print(f"  Expected: {r['expected_any']}")
            print(f"  Got: {h['section_num']}:{h['moment']} score={h['score']:.4f}")
        print()

print(f"MUST Top-1 rate: {must_top1_pass}/{must_total} = {must_top1_pass/must_total:.1%}")

