# Kuntalaki Retrieval Evaluation Report

## Summary

- **Total questions**: 80
- **MUST questions**: 8
- **SHOULD questions**: 72

## Pass Rates

| Metric | Value |
|--------|-------|
| PASS rate (TOTAL) | **91.2%** |
| PASS rate (MUST) | **100.0%** |
| PASS rate (SHOULD) | **90.3%** |
| MRR@k | **0.855** |

## Score Statistics

| Metric | Value |
|--------|-------|
| Avg top-1 score | 0.678 |
| Median top-1 score | 0.684 |
| Min top-1 score | 0.519 |
| Max top-1 score | 0.811 |
| Avg latency | 42.6 ms |

## Pass Rate by Category

| Category | Pass Rate |
|----------|----------|
| arviointimenettely | 90.9% |
| covid-poikkeus | 66.7% |
| hallinto | 100.0% |
| kirjanpito | 100.0% |
| konserni | 100.0% |
| kuntayhtymä | 100.0% |
| laina | 100.0% |
| osallistuminen | 100.0% |
| päätöksenteko | 100.0% |
| siirtymäsäännökset | 100.0% |
| talousarvio | 92.3% |
| tilinpäätös | 85.7% |
| tilintarkastus | 100.0% |
| toimintakertomus | 40.0% |
| valtuusto | 100.0% |

## Failed Questions

| ID | Type | Category | Query |
|----|------|----------|-------|
| KL-SHOULD-014 | SHOULD | arviointimenettely | Kriisikunnan tunnusmerkit ja kriteerit |
| KL-SHOULD-045 | SHOULD | covid-poikkeus | Koronaepidemia ja kunnan talous |
| KL-SHOULD-013 | SHOULD | talousarvio | Talousarvion sitovuus ja määrärahat |
| KL-SHOULD-018 | SHOULD | tilinpäätös | Kunnan tilinpäätöksen hyväksymisen aikataulu |
| KL-SHOULD-024 | SHOULD | toimintakertomus | Sisäinen valvonta ja riskienhallinta toimintakerto... |
| KL-SHOULD-025 | SHOULD | toimintakertomus | Alijäämäselvitys toimintakertomuksessa |
| KL-SHOULD-051 | SHOULD | toimintakertomus | Olennaiset tapahtumat tilikauden päättymisen jälke... |

## Quality Gates

- Gate A (MUST >= 95%): PASS (100.0%)
- Gate B (TOTAL >= 90%): PASS (91.2%)
- Gate C (Latency < 150ms): PASS (42.6 ms)
