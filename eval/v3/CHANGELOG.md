# Eval v3 Questions Changelog

Tämä tiedosto dokumentoi kaikki muutokset `questions_kuntalaki_v3.json`-tiedostoon.

---

## 2026-01-04: v4 anchors & pair-guards

### Korjatut kysymykset

| ID | Muutos | Syy | Lakiviite |
|----|--------|-----|-----------|
| KL-SHOULD-024 | expected: 115:2 → 115:1 | Sisäinen valvonta on §115:1:ssä | KL 115 § 1 mom |
| KL-SHOULD-025 | expected: 115:3 → 115:2 | Alijäämäselvitys on §115:2:ssa | KL 115 § 2 mom |
| KL-HARD-005 | expected: 115:2 → 115:1 | Sisäinen valvonta on §115:1:ssä | KL 115 § 1 mom |
| KL-PREC-009 | expected: 115:2 → 115:1 | Sisäinen valvonta on §115:1:ssä | KL 115 § 1 mom |
| KL-PREC-010 | expected: 115:3 → 115:2 | Alijäämäselvitys on §115:2:ssa | KL 115 § 2 mom |
| KL-MUST-001 | laajennettu expected_any | 148:2 on myös validi vastaus | KL 148 § 2 mom |
| KL-MUST-008 | laajennettu expected_any | 148:3 on myös validi vastaus | KL 148 § 3 mom |

### Huomioita

- §115 momenttien sisältö varmistettu Finlex XML:stä:
  - 115:1 = tavoitteet, olennaiset asiat, **sisäinen valvonta, riskienhallinta**
  - 115:2 = **alijäämäselvitys** (jos taseessa alijäämää)
  - 115:3 = tuloskäsittely

---


## 2026-01-04: v4 KL-SHOULD-051 korjaus

| ID | Muutos | Syy | Lakiviite |
|----|--------|-----|-----------|
| KL-SHOULD-051 | "Olennaiset tapahtumat..." -> "Toimintakertomuksessa olennaiset asiat..." | Alkuperainen kysymys ei vastannut lakitekstiä | KL 115 § 1 mom |
| KL-SHOULD-051-P01 | "merkittavat tapahtumat..." -> "Mitka olennaiset asiat..." | Parafraasi korjattu | KL 115 § 1 mom |
| KL-SHOULD-051-P02 | "tarkeat tapahtumat..." -> "Arvio tulevasta kehityksesta..." | Parafraasi korjattu | KL 115 § 1 mom |

Perustelu: §115:1 puhuu "olennaisista ASIOISTA" ja "arviosta todennakoisesta tulevasta kehityksesta", 
ei "tilikauden jalkeiset tapahtumat". Alkuperainen kysymys ei siis vastannut lakitekstiä.

## Tulevat korjaukset (v4)

| ID | Suunniteltu muutos | Syy |
|----|-------------------|-----|
| KL-SHOULD-051 | Muotoile kysymys uudelleen | "Olennaiset tapahtumat tilikauden päättymisen jälkeen" ei vastaa §115:1 sisältöä |


