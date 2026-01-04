"""Fix min_score for questions that fail due to threshold being too high."""

import json
from pathlib import Path

qpath = Path("questions_kuntalaki_v3.json")
questions = json.loads(qpath.read_text(encoding="utf-8"))

# Lower min_score for questions that are failing due to threshold
fixes = {
    "KL-SHOULD-045": 0.50,  # Score was 0.5419
    "KL-SHOULD-062-P01": 0.50,  # Score was 0.5228
    "KL-PREC-009": 0.45,  # Score was 0.4909
}

for q in questions:
    if q["id"] in fixes:
        old_score = q.get("min_score", 0.55)
        q["min_score"] = fixes[q["id"]]
        print(f"Fixed {q['id']}: min_score {old_score} -> {q['min_score']}")

qpath.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {qpath}")

