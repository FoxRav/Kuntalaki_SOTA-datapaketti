"""Expand MUST question expected_any to include valid alternative moments."""

import json
from pathlib import Path

qpath = Path("questions_kuntalaki_v3.json")
questions = json.loads(qpath.read_text(encoding="utf-8"))

fixes = {
    # KL-MUST-001: alijäämän kattamisesta - 148:2 and 148:3 are also valid
    "KL-MUST-001": [
        {"section": "110", "moment": "3"},
        {"section": "148", "moment": "1"},
        {"section": "148", "moment": "2"},  # 2022 deadline
    ],
    # KL-MUST-004: tilinpäätökseen kuuluu - 113:1 defines tilikausi
    "KL-MUST-004": [
        {"section": "113", "moment": "1"},
        {"section": "113", "moment": "2"},
    ],
    # KL-MUST-008: siirtymäsäännös - all 148 moments are siirtymäsäännöksiä
    "KL-MUST-008": [
        {"section": "148", "moment": "1"},
        {"section": "148", "moment": "2"},
        {"section": "148", "moment": "3"},
    ],
}

for q in questions:
    if q["id"] in fixes:
        q["expected_any"] = fixes[q["id"]]
        print(f"Fixed {q['id']}: expected_any = {q['expected_any']}")

qpath.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {qpath}")

