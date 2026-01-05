# v9: Document Graph Layer

Tilinpäätösasiakirjojen rakenteellinen graafi + Law↔Report Mapping.

## Arkkitehtuuri

```
docs_layer/
├─ data/
│  └─ <city>/
│     └─ <year>/
│        ├─ raw/              # PDF (ei gitissä)
│        ├─ parsed/           # Structured JSON
│        └─ graph/
│           ├─ nodes.jsonl
│           └─ edges.jsonl
├─ scripts/
│  ├─ parse_pdf.py            # PDF → structured JSON
│  ├─ build_document_graph.py # JSON → graph
│  ├─ build_document_index.py # chunks → Chroma
│  └─ map_law_to_doc.py       # law_node → doc_node
├─ eval/
│  └─ real_doc/
│     ├─ questions.json
│     ├─ results.json
│     └─ report.md
└─ README.md
```

## Document Graph Schema

### Node Types
- `DOC`: Asiakirja (koko tilinpäätös)
- `PAGE`: Sivu
- `SECTION`: Otsikko / alaluku
- `TABLE`: Taulukko
- `ROW`: Taulukon rivi
- `CELL`: Taulukon solu
- `PARA`: Tekstikappale
- `METRIC`: Tunnusluku (esim. vuosikate, nettoinvestoinnit)

### Edge Types
- `HAS_PAGE`: DOC → PAGE
- `HAS_SECTION`: PAGE/SECTION → SECTION
- `HAS_TABLE`: SECTION → TABLE
- `HAS_PARA`: SECTION → PARA
- `HAS_ROW`: TABLE → ROW
- `HAS_CELL`: ROW → CELL
- `NEXT`: Järjestysedge
- `REFERS_TO`: Viittaus toiseen kohtaan
- `DERIVED_FROM`: METRIC ← CELL/ROW (laskentakaava)

## Law↔Report Mapping Edge Types
- `REQUIRES_DISCLOSURE`: law_node → doc_node (laki vaatii tiedon)
- `GOVERNS`: law_node → doc_section (laki sääntelee)
- `EVIDENCED_BY`: law_node → table/cell (todiste datassa)
- `RISK_FLAG`: law_node → doc_node (poikkeus/riski)

## Node ID Format

```
<city>:<year>:<type>:<path>
```

Esimerkit:
- `lapua:2023:DOC:tilinpaatos`
- `lapua:2023:PAGE:15`
- `lapua:2023:SECTION:toimintakertomus:talous`
- `lapua:2023:TABLE:tuloslaskelma:1`
- `lapua:2023:METRIC:vuosikate`

## Eval Metrics (v9)

| Metric | Kuvaus | Tavoite |
|--------|--------|---------|
| LAW_PASS | Oikea laki/pykälä/momentti | ≥ 95% |
| DOC_PASS | Oikea raportin kohta | ≥ 85% |
| EVIDENCE_PASS | Ankkurit löytyvät | ≥ 85% |
| Latency | Dok-haku + mapping | < 250ms |

## Status ✅

- [x] Document Graph builder (81 nodes, 82 edges)
- [x] Document index (70 indexed documents)
- [x] Mapping engine (interactive mode)
- [x] Real-doc eval (29 questions)

## Eval Results (v9)

| Metric | Result | Gate | Status |
|--------|--------|------|--------|
| **LAW_PASS** | 96.6% | ≥95% | ✅ |
| **DOC_PASS** | 100.0% | ≥85% | ✅ |
| **EVIDENCE_PASS** | 89.7% | ≥85% | ✅ |
| **Latency** | 97.7ms | <250ms | ✅ |

**ALL v9 QUALITY GATES PASS** ✅

