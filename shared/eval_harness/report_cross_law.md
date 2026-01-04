# Cross-Law Evaluation Report (v6)

**Generated:** 2026-01-05T00:16:38.934057
**Config:** k=10, min_score=0.5

## Quality Gates

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
| Pass Rate | >= 95% | 55.0% | FAIL |
| Hard Negatives | = 0 | 0 | PASS |
| Latency | < 150ms | 35.8ms | PASS |

**Overall Gate Status:** FAIL

## Summary

- **Total Questions:** 100
- **Passed:** 55 (55.0%)
- **Top-1 Hits:** 42 (42.0%)
- **Hard Negative Violations:** 0
- **Avg Latency:** 35.8ms

## Per-Pair Metrics

| Pair | Total | Passed | Pass% | Top-1% | HN-Viol |
|------|-------|--------|-------|--------|---------|
| HANK | 20 | 11 | 55.0% | 50.0% | 0 |
| KPA | 20 | 7 | 35.0% | 25.0% | 0 |
| KPL | 20 | 11 | 55.0% | 40.0% | 0 |
| OYL | 20 | 13 | 65.0% | 45.0% | 0 |
| TILA | 20 | 13 | 65.0% | 50.0% | 0 |

## Failed Questions

- **CROSS-KUNTA-HANK-003**: tarjouksen valintaperusteet...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 93, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §131 (score: 0.5879)
- **CROSS-KUNTA-HANK-005**: kunnan investointien rahoitus...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 110, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §6 (score: 0.5442)
- **CROSS-KUNTA-HANK-008**: kunnan toiminnan ja talouden ohjaus...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 110, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §120 (score: 0.6379)
- **CROSS-KUNTA-HANK-012**: tarjoajan poissulkemisperusteet...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 80, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §131 (score: 0.5207)
- **CROSS-KUNTA-HANK-014**: valtuuston päätös suuresta investoinnista...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 14, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §111 (score: 0.5129)
- **CROSS-KUNTA-HANK-015**: neuvottelumenettely julkisissa hankinnoissa...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 34, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §12 (score: 0.5810)
- **CROSS-KUNTA-HANK-018**: sosiaalinen näkökulma hankinnoissa...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 98, 'moment': 1}]
  - Top-1: No results
- **CROSS-KUNTA-HANK-019**: käyttöoikeussopimus ja konsessio...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 4, 'moment': 1}]
  - Top-1: No results
- **CROSS-KUNTA-HANK-020**: avoin menettely ja rajoitettu menettely...
  - Expected: [{'law_key': 'hankintalaki_1397_2016', 'section_num': 32, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §131 (score: 0.5336)
- **CROSS-KUNTA-KPA-002**: taseen vastaavaa ja vastattavaa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 6, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §1 (score: 0.5670)
- **CROSS-KUNTA-KPA-007**: pysyvät vastaavat taseessa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 6, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §3 (score: 0.6442)
- **CROSS-KUNTA-KPA-008**: kuntayhtymän tase...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 113, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §117 (score: 0.5625)
- **CROSS-KUNTA-KPA-009**: oma pääoma ja vieras pääoma taseessa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 6, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §5 (score: 0.6435)
- **CROSS-KUNTA-KPA-010**: tuloslaskelman henkilöstökulut...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §7 (score: 0.5403)
- **CROSS-KUNTA-KPA-011**: valtuuston päätös taseen osoittamasta tuloksesta...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 113, 'moment': 3}]
  - Top-1: kuntalaki_410_2015 §121 (score: 0.6328)
- **CROSS-KUNTA-KPA-012**: liiketoiminnan muut tuotot tuloslaskelmassa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §1 (score: 0.6064)
- **CROSS-KUNTA-KPA-013**: poistot ja arvonalentumiset tuloslaskelmassa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kirjanpitolaki_1336_1997 §18 (score: 0.5733)
- **CROSS-KUNTA-KPA-016**: vakuudet ja vastuusitoumukset liitetiedoissa...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 2, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §84 (score: 0.5463)
- **CROSS-KUNTA-KPA-017**: kunnanjohtajan allekirjoittama tilinpäätös...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 113, 'moment': 2}]
  - Top-1: kuntalaki_410_2015 §113 (score: 0.7213)
- **CROSS-KUNTA-KPA-018**: rahoitustuotot ja -kulut...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §113 (score: 0.5284)
- **CROSS-KUNTA-KPA-019**: pienyrityksen tilinpäätöskaava...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §118 (score: 0.5313)
- **CROSS-KUNTA-KPA-020**: vaihtuvat vastaavat ja vaihto-omaisuus...
  - Expected: [{'law_key': 'kirjanpitoasetus_1339_1997', 'section_num': 6, 'moment': 1}]
  - Top-1: No results
- **CROSS-KUNTA-KPL-007**: kirjanpidon menetelmät ja aineisto...
  - Expected: [{'law_key': 'kirjanpitolaki_1336_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §112 (score: 0.5376)
- **CROSS-KUNTA-KPL-009**: rahoituslaskelma ja kassavirta...
  - Expected: [{'law_key': 'kirjanpitolaki_1336_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kirjanpitoasetus_1339_1997 §1 (score: 0.6813)
- **CROSS-KUNTA-KPL-010**: tilinpäätöksen allekirjoitus ja päiväys...
  - Expected: [{'law_key': 'kirjanpitolaki_1336_1997', 'section_num': 7, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §113 (score: 0.6420)
- **CROSS-KUNTA-KPL-011**: valtuuston hyväksymä tilinpäätös...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 113, 'moment': 3}]
  - Top-1: kuntalaki_410_2015 §110 (score: 0.6324)
- **CROSS-KUNTA-KPL-012**: liikevaihdon ja tuottojen kirjaaminen...
  - Expected: [{'law_key': 'kirjanpitolaki_1336_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §120 (score: 0.5508)
- **CROSS-KUNTA-KPL-013**: konsernitilinpäätös kirjanpidossa...
  - Expected: [{'law_key': 'kirjanpitolaki_1336_1997', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §114 (score: 0.7346)
- **CROSS-KUNTA-KPL-015**: tilinpäätöksen julkistaminen ja rekisteröinti...
  - Expected: [{'law_key': 'kirjanpitolaki_1336_1997', 'section_num': 9, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §113 (score: 0.5782)
- **CROSS-KUNTA-KPL-017**: kunnanhallituksen vastuu tilinpäätöksestä...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 113, 'moment': 2}]
  - Top-1: kuntalaki_410_2015 §39 (score: 0.6717)
- **CROSS-KUNTA-KPL-020**: tilikauden pituus ja muuttaminen...
  - Expected: [{'law_key': 'kirjanpitolaki_1336_1997', 'section_num': 4, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §113 (score: 0.5676)
- **CROSS-KUNTA-OYL-002**: yhtiökokouksen päätöksenteko...
  - Expected: [{'law_key': 'osakeyhtiolaki_624_2006', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §98 (score: 0.6044)
- **CROSS-KUNTA-OYL-007**: osingon jakaminen yhtiössä...
  - Expected: [{'law_key': 'osakeyhtiolaki_624_2006', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §150 (score: 0.5079)
- **CROSS-KUNTA-OYL-010**: hallituksen jäsenen vahingonkorvausvastuu...
  - Expected: [{'law_key': 'osakeyhtiolaki_624_2006', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §109 (score: 0.5201)
- **CROSS-KUNTA-OYL-013**: osakkeen luovuttaminen ja siirto...
  - Expected: [{'law_key': 'osakeyhtiolaki_624_2006', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §150 (score: 0.5838)
- **CROSS-KUNTA-OYL-014**: valtuuston päätös tytäryhtiön perustamisesta...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 14, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §47 (score: 0.5780)
- **CROSS-KUNTA-OYL-016**: pörssiyhtiön hallinto...
  - Expected: [{'law_key': 'osakeyhtiolaki_624_2006', 'section_num': 16, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §67 (score: 0.5321)
- **CROSS-KUNTA-OYL-020**: osakeannin toteuttaminen...
  - Expected: [{'law_key': 'osakeyhtiolaki_624_2006', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §150 (score: 0.5129)
- **CROSS-KUNTA-TILA-006**: tilintarkastusyhteisön hyväksyminen...
  - Expected: [{'law_key': 'tilintarkastuslaki_1141_2015', 'section_num': 1, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §122 (score: 0.6504)
- **CROSS-KUNTA-TILA-007**: tilintarkastusvelvollisuus yhtiössä...
  - Expected: [{'law_key': 'tilintarkastuslaki_1141_2015', 'section_num': 2, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §123 (score: 0.6452)
- **CROSS-KUNTA-TILA-010**: mukautettu tilintarkastuslausunto...
  - Expected: [{'law_key': 'tilintarkastuslaki_1141_2015', 'section_num': 5, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §125 (score: 0.5464)
- **CROSS-KUNTA-TILA-012**: hyvä tilintarkastustapa...
  - Expected: [{'law_key': 'tilintarkastuslaki_1141_2015', 'section_num': 3, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §123 (score: 0.5815)
- **CROSS-KUNTA-TILA-016**: tilintarkastusvalvonta ja PRH...
  - Expected: [{'law_key': 'tilintarkastuslaki_1141_2015', 'section_num': 7, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §122 (score: 0.5251)
- **CROSS-KUNTA-TILA-017**: kunnan ulkoinen tarkastus ja valvonta...
  - Expected: [{'law_key': 'kuntalaki_410_2015', 'section_num': 122, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §121 (score: 0.5581)
- **CROSS-KUNTA-TILA-018**: pörssiyhtiön tilintarkastus...
  - Expected: [{'law_key': 'tilintarkastuslaki_1141_2015', 'section_num': 5, 'moment': 1}]
  - Top-1: kuntalaki_410_2015 §123 (score: 0.5598)