# v9 Real-doc Eval Report

## Summary

| Gate | Value | Target | Status |
|------|-------|--------|--------|
| **LAW_PASS** | 96.6% | >= 95% | PASS |
| **DOC_PASS** | 100.0% | >= 85% | PASS |
| **EVIDENCE_PASS** | 89.7% | >= 85% | PASS |
| **Latency** | 97.7ms | < 250ms | PASS |

**OVERALL: PASS**

## Detailed Results

| ID | Query | LAW | DOC | EVIDENCE | Latency |
|----|-------|-----|-----|----------|---------|
| REAL-COMPLIANCE-001 | Onko Lapuan kaupungin tilinpäätös laadit... | Pass | Pass | Pass | 484ms |
| REAL-COMPLIANCE-002 | Sisältääkö toimintakertomus selvityksen ... | Pass | Pass | Pass | 65ms |
| REAL-COMPLIANCE-003 | Onko konsernitilinpäätös laadittu kuntal... | Pass | Pass | Pass | 84ms |
| REAL-COMPLIANCE-004 | Onko takaukset esitetty liitetiedoissa k... | Pass | Pass | Pass | 152ms |
| REAL-DISCLOSURE-001 | Mitä tietoja toimintakertomuksessa on es... | Pass | Pass | Pass | 68ms |
| REAL-DISCLOSURE-002 | Miten vuosikate on esitetty tuloslaskelm... | Pass | Pass | Pass | 72ms |
| REAL-DISCLOSURE-003 | Miten oma pääoma on esitetty taseessa? | Pass | Pass | Pass | 166ms |
| REAL-DISCLOSURE-004 | Miten liitetiedot on laadittu kirjanpito... | Pass | Pass | Pass | 66ms |
| REAL-METRIC-001 | Mikä oli Lapuan kaupungin vuosikate vuon... | FAIL | Pass | FAIL | 66ms |
| REAL-METRIC-002 | Mikä oli tilikauden tulos 2023? | Pass | Pass | Pass | 68ms |
| REAL-METRIC-003 | Paljonko kaupungilla on takauksia? | Pass | Pass | Pass | 63ms |
| REAL-METRIC-004 | Mikä on kaupungin lainakanta? | Pass | Pass | Pass | 148ms |
| REAL-RISK-001 | Onko kaupungin taloudellinen tilanne arv... | Pass | Pass | FAIL | 93ms |
| REAL-RISK-002 | Mitkä ovat merkittävimmät riskit toimint... | Pass | Pass | Pass | 82ms |
| REAL-RISK-003 | Onko alijäämän kattamisvelvollisuutta ku... | Pass | Pass | FAIL | 80ms |
| REAL-AUDIT-001 | Onko tilintarkastaja antanut huomautukse... | Pass | Pass | Pass | 159ms |
| REAL-AUDIT-002 | Antaako tilintarkastuskertomus puhtaan l... | Pass | Pass | Pass | 73ms |
| REAL-CROSS-001 | Miten kuntalaki ja kirjanpitolaki yhdess... | Pass | Pass | Pass | 81ms |
| REAL-CROSS-002 | Mihin kirjanpitolain kohtiin viitataan t... | Pass | Pass | Pass | 66ms |
| REAL-TABLE-001 | Mitä tuloslaskelman rivit kertovat toimi... | Pass | Pass | Pass | 67ms |
| REAL-TABLE-002 | Mitä taseen vastaavaa-puoli sisältää? | Pass | Pass | Pass | 78ms |
| REAL-TABLE-003 | Miten rahoituslaskelman rahavirrat on es... | Pass | Pass | Pass | 81ms |
| REAL-DISCLOSURE-005 | Miten pysyvien vastaavien arvostusperiaa... | Pass | Pass | Pass | 70ms |
| REAL-COMPLIANCE-005 | Onko toimintakertomuksen sisältö kuntala... | Pass | Pass | Pass | 74ms |
| REAL-METRIC-005 | Mikä on toimintakate? | Pass | Pass | Pass | 66ms |
| REAL-DISCLOSURE-006 | Miten konsernin tuloslaskelma eroaa kaup... | Pass | Pass | Pass | 65ms |
| REAL-RISK-004 | Onko kaupungin velkaantuneisuus kohtuull... | Pass | Pass | Pass | 67ms |
| REAL-AUDIT-003 | Onko vastuuvapaus myönnettävissä tilinpä... | Pass | Pass | Pass | 61ms |
| REAL-COMPLIANCE-006 | Onko tilinpäätös allekirjoitettu määräaj... | Pass | Pass | Pass | 68ms |

## Failures

### REAL-METRIC-001
- Query: Mikä oli Lapuan kaupungin vuosikate vuonna 2023?
- LAW_PASS: False
- DOC_PASS: True
- Doc Top-1: lapua:2023:PARA:tilintarkastuskertomus:p0
