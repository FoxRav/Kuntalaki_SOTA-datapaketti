# Cross-Law Evaluation Report (v7)

**Generated:** 2026-01-05T00:29:20.307263
**Config:** k=10, min_score=0.5

## Quality Gates (STRICT)

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
| Pass Rate STRICT | >= 95% | 61.0% | FAIL |
| Hard Negatives | = 0 | 1 | FAIL |
| Latency | < 150ms | 44.5ms | PASS |

**Overall Gate Status:** FAIL

## Summary

### STRICT (law_key + section_num + moment match) - **GATE**
- **Passed:** 61/100 (61.0%)
- **Top-1 Hits:** 38 (38.0%)

### ROUTING (law_key match only) - *diagnostic*
- **Passed:** 71/100 (71.0%)
- **Top-1 Hits:** 68 (68.0%)

### Other
- **Hard Negative Violations:** 1
- **Avg Latency:** 44.5ms

## Per-Pair Metrics

| Pair | Total | STRICT | STRICT% | ROUTING% | Top1-S | HN |
|------|-------|--------|---------|----------|--------|-----|
| HANK | 20 | 11 | 55.0% | 70.0% | 30.0% | 0 |
| KPA | 20 | 9 | 45.0% | 50.0% | 30.0% | 0 |
| KPL | 20 | 17 | 85.0% | 95.0% | 40.0% | 1 |
| OYL | 20 | 12 | 60.0% | 70.0% | 45.0% | 0 |
| TILA | 20 | 12 | 60.0% | 70.0% | 45.0% | 0 |

## Failed Questions (STRICT)

- **CROSS-KUNTA-HANK-001** [ROUTE-OK]: julkisen hankinnan kynnysarvot...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 2, 'moment': 3}]
  - Top-1: hankintalaki_1397_2016 §25.1 (score: 0.6991)
- **CROSS-KUNTA-HANK-003** [route-fail]: tarjouksen valintaperusteet...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 79, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §131.3 (score: 0.5879)
- **CROSS-KUNTA-HANK-007** [ROUTE-OK]: puitejärjestely ja hankintasopimus...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 136, 'moment': 1}]
  - Top-1: hankintalaki_1397_2016 §42.4 (score: 0.7372)
- **CROSS-KUNTA-HANK-012** [route-fail]: tarjoajan poissulkemisperusteet...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 81, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §131.3 (score: 0.5207)
- **CROSS-KUNTA-HANK-014** [ROUTE-OK]: valtuuston päätös suuresta investoinnista...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 118, 'moment': 6}]
  - Top-1: kuntalaki_410_2015 §111.1 (score: 0.5129)
- **CROSS-KUNTA-HANK-015** [route-fail]: neuvottelumenettely julkisissa hankinnoissa...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 36, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §12.1 (score: 0.5810)
- **CROSS-KUNTA-HANK-018** [route-fail]: sosiaalinen näkökulma hankinnoissa...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 108, 'moment': 2}]
  - Top-1: No results
- **CROSS-KUNTA-HANK-019** [route-fail]: käyttöoikeussopimus ja konsessio...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 117, 'moment': 2}]
  - Top-1: No results
- **CROSS-KUNTA-HANK-020** [route-fail]: avoin menettely ja rajoitettu menettely...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 33, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §131.3 (score: 0.5336)
- **CROSS-KUNTA-KPA-002** [route-fail]: taseen vastaavaa ja vastattavaa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 5, 'moment': 3}]
  - Top-1: kirjanpitolaki_1336_1997 §1.2 (score: 0.5670)
- **CROSS-KUNTA-KPA-007** [route-fail]: pysyvät vastaavat taseessa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 6, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §3.1 (score: 0.6442)
- **CROSS-KUNTA-KPA-009** [route-fail]: oma pääoma ja vieras pääoma taseessa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 6, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §5.1 (score: 0.6435)
- **CROSS-KUNTA-KPA-010** [route-fail]: tuloslaskelman henkilöstökulut...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 3, 'moment': 3}]
  - Top-1: kirjanpitolaki_1336_1997 §7.2 (score: 0.5403)
- **CROSS-KUNTA-KPA-011** [ROUTE-OK]: valtuuston päätös taseen osoittamasta tuloksesta...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 118, 'moment': 6}]
  - Top-1: kuntalaki_410_2015 §121.5 (score: 0.6328)
- **CROSS-KUNTA-KPA-012** [route-fail]: liiketoiminnan muut tuotot tuloslaskelmassa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 2, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §1.1 (score: 0.6064)
- **CROSS-KUNTA-KPA-013** [route-fail]: poistot ja arvonalentumiset tuloslaskelmassa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 2, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §18.1 (score: 0.5733)
- **CROSS-KUNTA-KPA-016** [route-fail]: vakuudet ja vastuusitoumukset liitetiedoissa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 7, 'moment': 2}]
  - Top-1: kirjanpitolaki_1336_1997 §5.1 (score: 0.5624)
- **CROSS-KUNTA-KPA-018** [route-fail]: rahoitustuotot ja -kulut...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 2, 'moment': 2}]
  - Top-1: kirjanpitolaki_1336_1997 §2.3 (score: 0.5862)
- **CROSS-KUNTA-KPA-019** [route-fail]: pienyrityksen tilinpäätöskaava...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §4.1 (score: 0.6258)
- **CROSS-KUNTA-KPA-020** [route-fail]: vaihtuvat vastaavat ja vaihto-omaisuus...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 6, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §4.2 (score: 0.6922)

*...and 19 more failed questions*

## Hard Negative Violations

- **CROSS-KUNTA-KPL-005**: kunnan tilinpäätöksen laatimisvelvollisuus...
  - Expected NOT: ['kirjanpitolaki_1336_1997']
  - Got Top-1: kirjanpitolaki_1336_1997 (VIOLATION)