"""Analyze failing questions to understand issues."""

import json
from pathlib import Path

results = json.loads(Path("kuntalaki_eval_v3_results.json").read_text(encoding="utf-8"))

# Find failing toimintakertomus questions
print("=== TOIMINTAKERTOMUS FAILURES ===\n")
for r in results["results"]:
    if r["category"] == "toimintakertomus" and not r["passed"]:
        print(f"ID: {r['id']}")
        print(f"Query: {r['query'][:70]}...")
        print(f"Expected: {r['expected_any']}")
        print("Top-3 hits:")
        for i, h in enumerate(r["hits"][:3], 1):
            boost = h.get("boost_applied", 0)
            print(f"  {i}. {h['section_num']}:{h['moment']} score={h['score']:.4f} boost={boost:.4f}")
        print()

print("\n=== HARD NEGATIVE VIOLATIONS ===\n")
for r in results["results"]:
    if r.get("hard_negative_violation"):
        print(f"ID: {r['id']}")
        print(f"Query: {r['query'][:70]}...")
        print(f"Expected: {r['expected_any']}")
        print(f"Forbidden (expected_none): {r['expected_none']}")
        print("Top-1 hit:")
        if r["hits"]:
            h = r["hits"][0]
            print(f"  {h['section_num']}:{h['moment']} score={h['score']:.4f}")
        print()

