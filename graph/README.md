# v8.1: Structural Legal Graph

Graph-guided Legal RAG layer that extends v7.2 retrieval with explicit structure-aware context expansion.

## Eval Results (v8.1)

| Metric | Result | Gate | Status |
|--------|--------|------|--------|
| **PRIMARY_PASS** | 100.0% | ≥90% | ✅ |
| **GRAPH_PATH_PASS** | 100.0% | ≥85% | ✅ |
| **SUPPORT_PASS** | 100.0% | ≥80% | ✅ |
| **Latency** | 109.7ms | <150ms | ✅ |

**ALL v8.1 QUALITY GATES PASS** ✅

## Overview

The legal graph enables:
- **Reference chain traversal**: Follow `REFERS_TO` edges to linked sections
- **Exception detection**: Surface `EXCEPTS` edges that modify applicability
- **Definition lookup**: Find `DEFINES` edges for term definitions
- **Normipolku generation**: Show the complete legal path from query to answer

## Architecture

```
┌────────────────────┐
│  v7.2 Retrieval    │  ← Multi-law query + rerank
└─────────┬──────────┘
          │ top-k hits
          ▼
┌────────────────────┐
│  Graph Expansion   │  ← 1-2 hop traversal
│  (REFERS_TO,       │
│   EXCEPTS, DEFINES)│
└─────────┬──────────┘
          │ expanded context
          ▼
┌────────────────────┐
│  Normipolku        │  ← Primary + supporting nodes + path
│  (extractive)      │
└────────────────────┘
```

## Files

### Graph Data
- `nodes.jsonl` - All moment nodes (2648 nodes)
- `edges.jsonl` - All edges (4412 edges)
- `graph_summary.json` - Statistics

### Scripts
- `scripts/build_structural_legal_graph.py` - Build graph from JSONL
- `scripts/graph_debug.py` - CLI for querying graph
- `scripts/graph_context_builder.py` - Context expansion module
- `scripts/graph_guided_query.py` - Full graph-guided query tool
- `scripts/run_graph_eval.py` - Evaluation runner

### Eval
- `graph/eval/questions_graph_needed.json` - Test questions
- `graph/eval/results_graph_needed.json` - Results
- `graph/eval/report_graph_needed.md` - Report

## Edge Types

| Type | Count | Description |
|------|-------|-------------|
| REFERS_TO (internal) | 1093 | Internal section references |
| REFERS_TO (external) | 147 | External law references |
| EXCEPTS | 56 | Exception/override clauses |
| DEFINES | 133 | Definition contexts |
| HAS_SECTION | 410 | Law → Section hierarchy |
| HAS_MOMENT | 2648 | Section → Moment hierarchy |
| **TOTAL** | **4487** | - |

## Usage

### Build Graph
```bash
python scripts/build_structural_legal_graph.py
```

### Query Graph
```bash
# Interactive mode
python scripts/graph_guided_query.py --interactive

# Single query
python scripts/graph_guided_query.py "kunnan tilinpäätöksen laatimisvelvollisuus"
```

### Debug Graph
```bash
# Show stats
python scripts/graph_debug.py --stats

# Query node neighbors
python scripts/graph_debug.py --node "410/2015:fin@20230780:6:1" --hops 2

# Query section
python scripts/graph_debug.py --section 113 --law 410
```

### Run Eval
```bash
python scripts/run_graph_eval.py
```

## Metrics

| Metric | Description | v8.1 Gate |
|--------|-------------|-----------|
| PRIMARY_PASS | Primary hit matches expected | ≥ 90% |
| GRAPH_PATH_PASS | Graph finds expected references | ≥ 85% |
| SUPPORT_PASS | Supporting nodes contain expected | ≥ 80% |
| Latency | Total query time | < 150 ms |

## Answer Format

```
======================================================================
GRAPH-GUIDED ANSWER
======================================================================

QUERY: kunnan tilinpäätöksen laatimisvelvollisuus

--- PRIMARY SOURCE ---
Law: kuntalaki_410_2015
Section: 113 - Tilinpäätös
Moment: 1
Score: 0.72

Text:
[Primary moment text]

--- SUPPORTING CONTEXT ---

EXCEPTIONS (poikkeukset):
  - kuntalaki_410_2015 2:1
    Soveltamisala
    [Exception text]

REFERENCES (viittaukset):
  - kirjanpitolaki_1336_1997 1:1
    Laatimisvelvollisuus
    [Referenced text]

--- NORMIPOLKU ---
  410/2015:...:113:1 --REFERS_TO--> external:1336/1997 [external law]
  410/2015:...:2:1 --EXCEPTS--> 410/2015:...:6:2

======================================================================
```

## Reference Patterns

The graph builder detects these patterns:

### Section References
- `X §` → REFERS_TO section X
- `X §:n Y momentissa` → REFERS_TO section X, moment Y

### Exception Keywords
- "poiketen", "poikkeuksena", "jollei", "sen estämättä" → EXCEPTS

### Definition Keywords
- "tarkoitetaan", "tässä laissa", "käsitteellä" → DEFINES

### External Law References
- `lain (XXXX/YYYY)` → REFERS_TO external law
- Named laws: `kirjanpitolakia`, `tilintarkastuslakia`, etc. (v8.1)

## v8.1 Improvements

1. **Section-level neighbor expansion**: Graph context builder now searches all moments in the same section, not just the exact node_id. This captures references like "8 §:n 2 momentissa" when the primary hit is on a different moment.

2. **Named law reference parsing**: Added recognition for named law references without explicit ID (e.g., "kirjanpitolakia" → "1336/1997"). This increased external references from 55 to 147.

3. **Router hardening**: Strengthened municipal context detection ("kunnan", "kuntakonserni") to force Kuntalaki into top-2 routing.

4. **Law-mismatch penalty**: Added rerank penalty (-0.03) for non-Kuntalaki hits when query contains municipal anchors.

