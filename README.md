# Kunnallinen Talous Law Stack (v8)

**Suomen kunnallisen talous- ja valvontadomainin lainsäädäntö SOTA-tasoisena AI-analyysidatana.**

Finlexin Akoma Ntoso XML -muodosta muunnettuna momenttitason JSON/JSONL-dataksi, vektori-indeksillä (ChromaDB/bge-m3), deterministisellä query-time reitityksellä ja **graph-guided context expansionilla**.

## Lait

| Laki | Säädös | Momentteja | Tila |
|------|--------|-----------|------|
| **Kuntalaki** | 410/2015 | 421 | ✅ Indeksoitu |
| **Kirjanpitolaki** | 1336/1997 | 385 | ✅ Indeksoitu |
| **Kirjanpitoasetus** | 1339/1997 | 112 | ✅ Indeksoitu |
| **Tilintarkastuslaki** | 1141/2015 | 357 | ✅ Indeksoitu |
| **Hankintalaki** | 1397/2016 | 454 | ✅ Indeksoitu |
| **Osakeyhtiölaki** | 624/2006 | 919 | ✅ Indeksoitu |
| **Yhteensä** | - | **2648** | ✅ |

## Arkkitehtuuri

```
├── analysis_layer/           # Kuntalaki (legacy, toimii)
│   ├── json/                 # Normalisoitu JSON/JSONL
│   ├── embeddings/           # ChromaDB (EI repossa)
│   ├── query_boost.py        # Query-time boost/penalty
│   └── tests/                # Golden-set testit
│
├── laws/                     # Multi-laki rakenne (v5.1)
│   ├── kirjanpitolaki_1336_1997/
│   ├── kirjanpitoasetus_1339_1997/
│   ├── tilintarkastuslaki_1141_2015/
│   ├── hankintalaki_1397_2016/
│   └── osakeyhtiolaki_624_2006/
│
├── graph/                    # v8: Structural Legal Graph
│   ├── nodes.jsonl           # 2648 moment nodes
│   ├── edges.jsonl           # 4412 edges (REFERS_TO, EXCEPTS, DEFINES)
│   ├── graph_summary.json    # Statistics
│   └── eval/                 # Graph-needed eval
│
├── shared/                   # Jaettu infrastruktuuri
│   ├── law_catalog.json      # Lakikatalogi
│   ├── cross_refs.json       # Ristiinviittaukset
│   ├── schemas/              # Yhteinen datamoodi
│   ├── query_rules/          # Law router
│   │   └── law_router.py     # Deterministinen reititys
│   └── utils/                # Geneerinen law builder
│
├── scripts/                  # Ajoskriptit
│   ├── build_all_embeddings.py
│   ├── multi_law_query.py          # Multi-laki haku
│   ├── build_structural_legal_graph.py  # v8: Graafin rakentaja
│   ├── graph_guided_query.py       # v8: Graph-guided query
│   └── graph_context_builder.py    # v8: Context expansion
│
└── eval/                     # Evaluaatio
    └── v3/                   # 150 kysymyksen testipatteri
```

## Pikastartti

### 1. Kloonaa ja asenna

```bash
git clone https://github.com/FoxRav/Kuntalaki_SOTA-datapaketti.git
cd Kuntalaki_SOTA-datapaketti
pip install lxml chromadb sentence-transformers pytest
```

### 2. Hanki Finlex-data

```bash
# Lataa: https://data.finlex.fi/
# Pura: finlex_statute_consolidated/
```

### 3. Generoi indeksit

```bash
# Kuntalaki
python analysis_layer/build_kuntalaki_json.py
python analysis_layer/build_embeddings.py

# Kaikki muut lait kerralla
python scripts/build_all_embeddings.py
```

### 4. Testaa multi-laki haku

```bash
python scripts/multi_law_query.py
```

## Multi-laki reititys

```python
from shared.query_rules.law_router import route_query

# Deterministinen reititys avainsanojen perusteella
query = "tilinpäätöksen liitetiedot ja tase"
routes = route_query(query)
# {'kirjanpitolaki_1336_1997': 1.0}

query = "julkisen hankinnan kynnysarvo"
routes = route_query(query)
# {'hankintalaki_1397_2016': 1.0}

query = "osakeyhtiön hallituksen vastuu"
routes = route_query(query)
# {'osakeyhtiolaki_624_2006': 1.0}
```

## Testikyselyjen tulokset

```
Query: kunnan talousarvion alijäämä → Kuntalaki §110, §148, §110a ✅
Query: tilinpäätöksen liitetiedot → Kirjanpitolaki §1, §6, §13 ✅
Query: tilintarkastajan huomautus → Tilintarkastuslaki §1, §5 ✅
Query: julkisen hankinnan kynnysarvo → Hankintalaki §25, §26 ✅
Query: osakeyhtiön hallituksen vastuu → Osakeyhtiölaki §9, §16a ✅
```

## JSON-skeema (v5)

```json
{
  "law": "Kirjanpitolaki",
  "law_id": "1336/1997",
  "law_key": "fi:act:1336/1997",
  "node_id": "1336/1997:fin@20251006:3:1:1",
  "finlex_version": "fin@20251006",
  "chapter": "3 luku",
  "chapter_title": "Tilinpäätös",
  "section_id": "1",
  "section_title": "Tilinpäätöksen sisältö",
  "moment": "1",
  "text": "...",
  "tags": ["tilinpäätös", "tase", "tuloslaskelma"],
  "anchors": ["tilinpäätös", "tase", "tuloslaskelma", "liitetiedot"],
  "in_force": true
}
```

## Eval tulokset (Kuntalaki v4)

```
Configuration: k=10, min_score=0.50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL:     150/150 (100.0%) ✅
MUST:      50/50   (100.0%) ✅
SHOULD:    60/60   (100.0%) ✅
Top-1:     91.3%
Precision@1: 88.0%
MRR: 0.944
Latency: ~45ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Tilastot (v5.1)

| Laki | Momentteja | Kuvaus |
|------|-----------|--------|
| Kuntalaki | 421 | Kuntahallinon perusta |
| Kirjanpitolaki | 385 | Kirjanpitovelvollisuus |
| Kirjanpitoasetus | 112 | KPL:n täydentävä (liitetiedot) |
| Tilintarkastuslaki | 357 | Tilintarkastus |
| Hankintalaki | 454 | Julkiset hankinnat |
| Osakeyhtiölaki | 919 | Yhtiöoikeus |
| **Yhteensä** | **2648** | 6 lakia |

## SOTA-arviointi: 20 asiantuntijakysymystä ✅

| Tulos | Arvo |
|-------|------|
| **Oikein** | **20/20 (100%)** |
| **Latenssi** | **72.8ms** |
| **Verdict** | **SOTA-TASO SAAVUTETTU** |

Kaikki 20 asiantuntijatason kysymystä (talousammattilaisen näkökulmasta) tunnistivat oikean lain top-3:ssa.

## Cross-Law Eval (v7.2)

| Gate | Tavoite | Tulos | Tila |
|------|--------|--------|--------|
| **STRICT Pass Rate** | >= 95% | **100.0%** | ✅ PASS |
| **ROUTING Pass Rate** | >= 95% | **100.0%** | ✅ PASS |
| **Hard Negatives** | = 0 | **0** | ✅ PASS |
| **Latency** | < 150ms | **52.4ms** | ✅ PASS |

**OVERALL: PASS** ✅

## Graph-guided RAG (v8.1) ✅

| Metric | Tulos | Gate | Tila |
|--------|--------|------|------|
| **Nodes** | 2648 | - | - |
| **Edges** | 4487 | - | - |
| **PRIMARY_PASS** | **100.0%** | ≥ 90% | ✅ |
| **GRAPH_PATH_PASS** | **100.0%** | ≥ 85% | ✅ |
| **SUPPORT_PASS** | **100.0%** | ≥ 80% | ✅ |
| **Latency** | **109.7 ms** | < 150 ms | ✅ |

**OVERALL: 100% ALL v8.1 METRICS** ✅

Edge types:
- REFERS_TO (internal): 1093
- REFERS_TO (external): 147
- EXCEPTS: 56
- DEFINES: 133

v8.1 improvements:
- Section-level neighbor expansion (graph-context-builder)
- Named law reference parsing (kirjanpitolakia, tilintarkastuslakia etc.)
- Router hardening for municipal context
- Law-mismatch penalty for reranking

### Graph-guided Query

```bash
# Interactive mode
python scripts/graph_guided_query.py --interactive

# Single query with normipolku
python scripts/graph_guided_query.py "kuntalain tilinpäätös pykälä 113"
```

## Roadmap

1. ✅ **v4**: Kuntalaki SOTA (100% pass)
2. ✅ **v5**: Multi-laki rakenne + 5 lakia
3. ✅ **v5.1**: Kirjanpitoasetus (1339/1997)
4. ✅ **v6**: Cross-law eval framework (100 questions)
5. ✅ **v7**: Autofill + Top2-router (baseline)
6. ✅ **v7.1**: Router-bonus + Pair-guards (HN=0)
7. ✅ **v7.2**: Multi-law autofill + eval (**100% PASS**)
8. ✅ **SOTA**: 20 asiantuntijakysymystä (**20/20 = 100%**)
9. ✅ **v8**: Graph-guided Legal RAG (2648 nodes, 4412 edges)
10. ✅ **v8.1**: Graph-guided kovennus (**ALL GATES PASS**)
11. ✅ **v9**: Document Graph + Law↔Report Mapping (**ALL GATES PASS**)
12. ✅ **v10.1**: Adversarial Eval - Robustness Testing (**ALL GATES PASS**)
13. ✅ **v11**: Finance Eval - Table-aware Retrieval (**ALL GATES PASS**)

## Finance Eval - Table-aware Retrieval (v11) ✅

**Kuntatalous-ajattelu**: Taulukko-evidenssi pakollinen numerokysymyksille.

| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| **TABLE_EVIDENCE** | 100.0% | ≥90% | ✅ PASS |
| **NUMERIC_ACCURACY** | 100.0% | ≥95% | ✅ PASS |
| **CITATION_COVERAGE** | 86.4% | ≥85% | ✅ PASS |
| **ABSTAIN_CORRECT** | 100.0% | ≥90% | ✅ PASS |

**OVERALL: PASS**

Finance testit (60 kysymystä):
- **TABLE_NUMERIC** (18): Taulukko-lukukysymykset
- **TREND** (8): Vuosivertailu
- **RISK** (6): Riskianalyysi
- **LAW_FINANCE** (7): Lakikytkentä
- **CONSOLIDATION** (6): Konsernitiedot
- **ABSTAIN** (15): Out-of-scope kysymykset

```bash
# Run finance eval
python scripts/run_v11_finance_eval.py
```

---

## Adversarial Robustness Testing (v10.1) ✅

**Single-Source Metrics Contract** - all metrics derived from `v10_adversarial_results.json`.

| Gate | Value | Threshold | Status |
|------|-------|-----------|--------|
| **CONFUSION_FAIL_RATE** | 0.0% | ≤ 2% | ✅ PASS |
| **HALLU_EVIDENCE** | 0 | = 0 | ✅ PASS |
| **VERSION_DRIFT** | 0 | = 0 | ✅ PASS |
| **ABSTAIN_CORRECT** | 100.0% | ≥ 90% | ✅ PASS |

**OVERALL: PASS**

Adversarial testit (40 kysymystä):
- **LAW** (10): Confusion & synonym attacks
- **GRAPH** (10): Multi-hop & exception traps  
- **DOC** (10): Evidence & table attacks
- **ABSTAIN** (10): Unknown/out-of-scope/versioning

```bash
# Run adversarial eval + render reports
python scripts/run_v10_adversarial_eval.py
python scripts/render_v10_report.py
```

## Document Graph + Law↔Report Mapping (v9) ✅

| Metric | Tulos | Tavoite | Tila |
|--------|-------|---------|------|
| **LAW_PASS** | **96.6%** | ≥95% | ✅ |
| **DOC_PASS** | **100.0%** | ≥85% | ✅ |
| **EVIDENCE_PASS** | **89.7%** | ≥85% | ✅ |
| **Latency** | **97.7ms** | <250ms | ✅ |

**OVERALL: ALL v9 GATES PASS** ✅

Document Graph (Lapua 2023):
- Nodes: 81 (DOC, PAGE, SECTION, PARA, TABLE, ROW, METRIC)
- Edges: 82 (HAS_PAGE, HAS_SECTION, HAS_PARA, HAS_TABLE, HAS_ROW, NEXT)

v9 yhdistää:
1. Lakitekstin haun (v7.2)
2. Viittausketjut/poikkeukset (v8.1)
3. Tilinpäätösasiakirjan rakenteen

```bash
# Build document graph from structured JSON
python docs_layer/scripts/build_document_graph.py --input <parsed_json> --output <output_dir>

# Build document index
python docs_layer/scripts/build_document_index.py --graph <graph_dir> --output <chroma_dir>

# Interactive law↔doc mapping
python docs_layer/scripts/map_law_to_doc.py --interactive --doc-index <chroma_dir>

# Run real-doc eval
python docs_layer/scripts/run_real_doc_eval.py --questions <questions.json> --doc-index <chroma_dir> --output <output_dir>
```

## Lisenssi & lähde

- **Data**: [Finlex avoin data](https://data.finlex.fi/) (CC BY 4.0)
- **Koodi**: MIT

## Riippuvuudet

```bash
pip install lxml chromadb sentence-transformers pytest
```

**Windows**: Aseta ennen ajoa:
```powershell
$env:USE_TF="0"
$env:USE_TORCH="1"
```
