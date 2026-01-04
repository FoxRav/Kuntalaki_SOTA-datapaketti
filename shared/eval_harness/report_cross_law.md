# Cross-Law Evaluation Report (v7.1)

**Generated:** 2026-01-05T00:51:13.639842
**Config:** k=10, min_score=0.5, router_bonus=0.02, diversity_gap=0.02

## Quality Gates (STRICT)

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
| Pass Rate STRICT | >= 95% | 100.0% | PASS |
| Hard Negatives | = 0 | 0 | PASS |
| Latency | < 150ms | 52.4ms | PASS |

**Overall Gate Status:** PASS

## Summary

### STRICT (law_key + section_num + moment match) - **GATE**
- **Passed:** 98/98 (100.0%)
- **Top-1 Hits:** 98 (100.0%)

### ROUTING (law_key match only) - *diagnostic*
- **Passed:** 98/98 (100.0%)
- **Top-1 Hits:** 98 (100.0%)

### Other
- **Hard Negative Violations:** 0
- **Avg Latency:** 52.4ms

### v7.1 Rerank Stats
- **Router Bonus Applied:** 511 times
- **Pair Guards Applied:** 264 times
- **Diversity Swaps:** 0 times

## Per-Pair Metrics

| Pair | Total | STRICT | STRICT% | ROUTING% | Top1-S | HN |
|------|-------|--------|---------|----------|--------|-----|
| HANK | 18 | 18 | 100.0% | 100.0% | 100.0% | 0 |
| KPA | 20 | 20 | 100.0% | 100.0% | 100.0% | 0 |
| KPL | 20 | 20 | 100.0% | 100.0% | 100.0% | 0 |
| OYL | 20 | 20 | 100.0% | 100.0% | 100.0% | 0 |
| TILA | 20 | 20 | 100.0% | 100.0% | 100.0% | 0 |