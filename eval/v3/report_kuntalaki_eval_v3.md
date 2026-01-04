# Kuntalaki Retrieval Evaluation Report v3

## Summary

- **Total questions**: 150
- **MUST questions**: 8
- **SHOULD questions**: 142

## Pass Rates

| Metric | Value |
|--------|-------|
| PASS rate (TOTAL) | **94.7%** |
| PASS rate (MUST) | **100.0%** |
| PASS rate (SHOULD) | **94.4%** |
| Top-1 hit rate | **85.3%** |
| Top-1 hit rate (MUST) | **87.5%** |
| Precision@1 | **85.3%** |
| Precision@3 | **94.0%** |
| MRR@k | **0.892** |

## Score Statistics

| Metric | Value |
|--------|-------|
| Avg top-1 score | 0.673 |
| Median top-1 score | 0.672 |
| Avg latency | 37.6 ms |
| Hard negative violations | 0 |

## Quality Gates

| Gate | Status | Value |
|------|--------|-------|
| Gate 1 (MUST >= 99%) | PASS | 100.0% |
| Gate 1b (MUST Top-1 >= 80%) | PASS | 87.5% |
| Gate 2 (SHOULD >= 95%) | **FAIL** | 94.4% |
| Gate 3 (toimintakertomus >= 90%) | PASS | 100.0% |
| Gate 3 (covid-poikkeus >= 90%) | PASS | 100.0% |
| Gate 3 (arviointimenettely >= 90%) | PASS | 100.0% |
| Gate 4 (No hard negative violations) | PASS | 0 |
| Gate 5 (Latency < 150ms) | PASS | 37.6 ms |

**Overall**: SOME GATES FAIL

## Pass Rate by Category

| Category | Pass Rate |
|----------|----------|
| arviointimenettely | 100.0% |
| covid-poikkeus | 100.0% |
| hallinto | 100.0% |
| hard_negative | 90.0% |
| kirjanpito | 100.0% |
| konserni | 100.0% |
| kuntayhtymä | 100.0% |
| laina | 100.0% |
| osallistuminen | 100.0% |
| precision | 73.3% ⚠️ |
| päätöksenteko | 100.0% |
| siirtymäsäännökset | 100.0% |
| talousarvio | 94.4% |
| tilinpäätös | 85.7% ⚠️ |
| tilintarkastus | 100.0% |
| toimintakertomus | 100.0% |
| valtuusto | 100.0% |

## Pass Rate by Test Type

| Test Type | Pass Rate |
|-----------|----------|
| base | 97.5% |
| hard_negative | 87.5% |
| hard_negative_precision | 100.0% |
| precision_at_1 | 73.3% |
| section_synonym | 100.0% |
| synonym | 100.0% |

## Failed Questions

| ID | Type | Category | Test Type | Query |
|----|------|----------|-----------|-------|
| KL-HARD-001 | SHOULD | hard_negative | hard_negative | Alijäämän kattamisen perusmääräaika ilma... |
| KL-HARD-018 | SHOULD | hard_negative | hard_negative | Konserniohjeet ja omistajapoliittinen oh... |
| KL-PREC-003 | SHOULD | precision | precision_at_1 | Alijäämän kattamisvelvollisuus ja neljän... |
| KL-PREC-009 | SHOULD | precision | precision_at_1 | Sisäisen valvonnan ja riskienhallinnan j... |
| KL-PREC-011 | SHOULD | precision | precision_at_1 | Arviointimenettelyn käynnistäminen valti... |
| KL-PREC-015 | SHOULD | precision | precision_at_1 | Arviointiryhmän ehdotusten käsittely ja ... |
| KL-SHOULD-013 | SHOULD | talousarvio | base | Talousarvion sitovuus ja määrärahat |
| KL-SHOULD-018 | SHOULD | tilinpäätös | base | Kunnan tilinpäätöksen hyväksymisen aikat... |

