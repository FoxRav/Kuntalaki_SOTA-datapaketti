"""
Fix KL-SHOULD-051 to match actual §115:1 content.

Original query: "Olennaiset tapahtumat tilikauden päättymisen jälkeen"
Problem: §115:1 talks about "olennaiset ASIAT" and "tuleva kehitys", 
         not "tilikauden jälkeiset tapahtumat"

New query: "Toimintakertomuksessa esitettävät olennaiset asiat ja tuleva kehitys"
"""

import json
from pathlib import Path

qpath = Path("questions_kuntalaki_v3.json")
questions = json.loads(qpath.read_text(encoding="utf-8"))

fixes = {
    "KL-SHOULD-051": {
        "query": "Toimintakertomuksessa esitettavat olennaiset asiat ja tuleva kehitys",
        "notes": "v4: korjattu vastaamaan KL 115:1 sisaltoa (olennaiset ASIAT, ei tapahtumat)",
    },
    "KL-SHOULD-051-P01": {
        "query": "Mitkä olennaiset asiat toimintakertomuksessa on esitettava",
        "notes": "v4: korjattu vastaamaan KL 115:1 sisaltoa",
    },
    "KL-SHOULD-051-P02": {
        "query": "Arvio todennakoisesta tulevasta kehityksesta toimintakertomuksessa",
        "notes": "v4: korjattu vastaamaan KL 115:1 sisaltoa",
    },
}

fixed = 0
for q in questions:
    if q["id"] in fixes:
        fix = fixes[q["id"]]
        old_query = q["query"]
        q["query"] = fix["query"]
        q["notes"] = fix["notes"]
        print(f"Fixed {q['id']}:")
        print(f"  OLD: {old_query}")
        print(f"  NEW: {q['query']}")
        fixed += 1

print(f"\nFixed {fixed} questions")
qpath.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved to {qpath}")

# Update changelog
changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text(encoding="utf-8")

new_entry = """
## 2026-01-04: v4 KL-SHOULD-051 korjaus

| ID | Muutos | Syy | Lakiviite |
|----|--------|-----|-----------|
| KL-SHOULD-051 | "Olennaiset tapahtumat..." -> "Toimintakertomuksessa olennaiset asiat..." | Alkuperainen kysymys ei vastannut lakitekstiä | KL 115 § 1 mom |
| KL-SHOULD-051-P01 | "merkittavat tapahtumat..." -> "Mitka olennaiset asiat..." | Parafraasi korjattu | KL 115 § 1 mom |
| KL-SHOULD-051-P02 | "tarkeat tapahtumat..." -> "Arvio tulevasta kehityksesta..." | Parafraasi korjattu | KL 115 § 1 mom |

Perustelu: §115:1 puhuu "olennaisista ASIOISTA" ja "arviosta todennakoisesta tulevasta kehityksesta", 
ei "tilikauden jalkeiset tapahtumat". Alkuperainen kysymys ei siis vastannut lakitekstiä.
"""

if "KL-SHOULD-051 korjaus" not in changelog:
    changelog = changelog.replace("## Tulevat korjaukset", new_entry + "\n## Tulevat korjaukset")
    changelog_path.write_text(changelog, encoding="utf-8")
    print("Updated CHANGELOG.md")

