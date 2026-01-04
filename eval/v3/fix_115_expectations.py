"""Fix §115 moment expectations to match actual law content."""

import json
from pathlib import Path

# Load questions
qpath = Path("questions_kuntalaki_v3.json")
questions = json.loads(qpath.read_text(encoding="utf-8"))

# Fix mappings:
# - sisäinen valvonta/riskienhallinta → 115:1 (was 115:2)
# - alijäämäselvitys → 115:2 (was 115:3)
# - tuloskäsittely → 115:3 (correct)

sisainen_valvonta_queries = [
    "Sisäinen valvonta ja riskienhallinta toimintakertomuksessa",
    "riskienhallinta ja riskienhallinta toimintakertomuksessa",
    "valvonta ja riskit ja riskienhallinta toimintakertomuksessa",
    "Sisäisen valvonnan ja riskienhallinnan järjestämisen selostus toimintakertomuksessa",
    "Sisäisen valvonnan ja riskienhallinnan järjestämisen selostus",
]

alijaama_selvitys_queries = [
    "Alijäämäselvitys toimintakertomuksessa",
    "kertynyt alijäämäselvitys toimintakertomuksessa",
    "tasealijäämäselvitys toimintakertomuksessa",
    "Selvitys alijäämän kattamisesta toimintakertomuksessa",
    "Alijäämän kattamissuunnitelma toimintakertomuksessa jos alijäämää ei katettu",
]

fixed_count = 0

for q in questions:
    query = q.get("query", "")
    expected = q.get("expected_any", [])
    
    for exp in expected:
        if exp.get("section") == "115":
            # Check if this is a sisäinen valvonta query expecting 115:2
            if exp.get("moment") == "2" and any(sv in query for sv in ["valvonta", "riskienhallinta", "riskit"]):
                exp["moment"] = "1"
                print(f"Fixed {q['id']}: {query[:50]}... -> 115:1")
                fixed_count += 1
            
            # Check if this is an alijäämäselvitys query expecting 115:3
            elif exp.get("moment") == "3" and any(aj in query.lower() for aj in ["alijäämäselvitys", "alijäämän kattamis"]):
                exp["moment"] = "2"
                print(f"Fixed {q['id']}: {query[:50]}... -> 115:2")
                fixed_count += 1

# Also fix the paraphrase generator expectations
print(f"\nFixed {fixed_count} questions")

# Save updated questions
qpath.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved to {qpath}")

