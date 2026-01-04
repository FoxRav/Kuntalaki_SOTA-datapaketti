"""Fix remaining §115 expectations."""

import json
from pathlib import Path

qpath = Path("questions_kuntalaki_v3.json")
questions = json.loads(qpath.read_text(encoding="utf-8"))

fixed = 0
for q in questions:
    # Fix KL-HARD-005 and KL-PREC-009: sisäinen valvonta should be 115:1
    if q["id"] in ["KL-HARD-005", "KL-PREC-009"]:
        for exp in q.get("expected_any", []):
            if exp.get("section") == "115" and exp.get("moment") == "2":
                exp["moment"] = "1"
                print(f"Fixed {q['id']}: 115:2 -> 115:1")
                fixed += 1

print(f"\nFixed {fixed} questions")
qpath.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved to {qpath}")

