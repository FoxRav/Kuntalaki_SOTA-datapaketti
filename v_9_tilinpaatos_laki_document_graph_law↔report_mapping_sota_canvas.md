# v9 – Tilinpäätös + Laki: Document Graph + Law↔Report Mapping (SOTA)

## Tavoite
Rakennetaan “liiketalouden nero” -tasoinen järjestelmä, joka:
1) hakee oikein lakitekstin (v7.2)
2) seuraa viittausketjut/poikkeukset/määritelmät (v8.1)
3) **liittää nämä suoraan tilinpäätösasiakirjan kohtiin** (uusi v9)

v9:n ydin: **Document Graph** + **Law↔Report Mapping** + **Real-doc eval**.

---

## 1) Mitä v9 lisää (uusi kerros)

### 1.1 Document Graph (tilinpäätös)
Rakennetaan eksplisiittinen graafi tilinpäätösasiakirjoista:
- Nodes:
  - `DOC` (asiakirja)
  - `PAGE` (sivu)
  - `SECTION` (otsikko / alaluku)
  - `TABLE` (taulukko)
  - `ROW` / `CELL` (rivi/solu) [jos saatavilla]
  - `FIGURE` (kuva) [valinnainen]
  - `PARA` (kappale)
  - `METRIC` (tunnusluku: esim. vuosikate, nettoinvestoinnit)
- Edges:
  - `HAS_PAGE`, `HAS_SECTION`, `HAS_TABLE`, `HAS_PARA`
  - `NEXT` (järjestys)
  - `REFERS_TO` (viittaa)
  - `DERIVED_FROM` (METRIC ← CELL/ROW)

Tulos: dokumentti ei ole pelkkä tekstimassa vaan navigoitava rakenne.

### 1.2 Law↔Report Mapping (linkityskerros)
Luodaan linkit lakisolmuista raportin solmuihin:
- Edge-tyypit:
  - `REQUIRES_DISCLOSURE` (laki → raportin kohta)
  - `GOVERNS` (laki → raportin osa)
  - `EVIDENCED_BY` (laki → data/taulukko)
  - `RISK_FLAG` (laki → poikkeus/riski)

Linkitys tehdään **deterministisesti + haulla**, ei LLM-hallusinaatiolla.

---

## 2) v9 Pipeline (kysymys → analyysi)

### 2.1 Intent & scope
- Tunnista: käyttäjä kysyy
  - (A) lakisäännöstä
  - (B) tilinpäätöksen kohdasta
  - (C) compliance/poikkeama
  - (D) tunnusluvusta
  - (E) “miksi” (perusteltu normipolku)

### 2.2 Legal retrieval (v7.2)
- router + bge-m3 + chroma + deterministic rerank

### 2.3 Legal graph expansion (v8.1)
- normipolku: primary + support (ref/except/define)

### 2.4 Document retrieval
- hybrid retrieval tilinpäätöksestä:
  - BM25 + dense embedding
  - metadata: year, doc_type, section_title, table_title

### 2.5 Mapping step (uusi)
- Valitse 1–3 relevanttia raportin solmua
- Muodosta “evidence bundle”:
  - doc_node_id
  - excerpt (text/table cell)
  - page/section path
- Luo linkit: law_node → doc_node

### 2.6 Output
Palauta aina:
- **Normipolku** (laki)
- **Todisteet** (tilinpäätös: sivu/otsikko/taulukko)
- **Johtopäätös** (compliance / riski / huomio)

---

## 3) Rakennusvaiheet (commit-suunnitelma)

### 3.1 v9.0 – Document Graph builder
- `scripts/build_document_graph.py`
  - input: parsittu tilinpäätös (PDF→structured JSON)
  - output: `docs/<city>/<year>/graph/nodes.jsonl`, `edges.jsonl`

### 3.2 v9.1 – Document index
- `scripts/build_document_index.py`
  - chunkit: PARA + TABLE captions + ROW/CELL
  - metadata: page, section_path, table_id, year
  - store: Chroma/FAISS + BM25

### 3.3 v9.2 – Mapping engine
- `scripts/map_law_to_doc.py`
  - input: legal hits (primary+support)
  - query doc index for evidence
  - output: mapping edges + evidence bundle

### 3.4 v9.3 – Real-doc eval harness
- `eval/real_doc/questions.json`
  - expected: (law_node, doc_node_path) + anchor terms
- metrics:
  - `LAW_PASS` (oikea laki/pykälä/momentti)
  - `DOC_PASS` (oikea raportin kohta)
  - `EVIDENCE_PASS` (ankkurit löytyvät)
  - `COMPLIANCE_PASS` (jos kysymys on compliance)

---

## 4) Testausstrategia (SOTA, tuotanto)

### 4.1 Freeze testit
- cross-law v7.2
- expert-20
- graph-needed v8.1
- + uusi real-doc v9

### 4.2 Drift & adversarial
- synonyymit, taivutukset, harhaanjohtavat termit
- “kunta vs yhtiö” -sekoitukset
- pykäläviittaus ilman numeroa ("tämän lain mukaan")

### 4.3 Regression gates
- jokaisen PR:n jälkeen ajetaan:
  - v7.2 gate
  - v8.1 gate
  - v9 real-doc gate

---

## 5) Minimivaatimukset v9 real-doc -evalille
- vähintään 30 kysymystä (10 compliance, 10 disclosure, 10 metrics)
- jokaisessa expected:
  - law_node_id (primary)
  - doc_node_path (page/section/table)
  - anchor_terms (2–5)

Tavoite:
- LAW_PASS ≥ 95%
- DOC_PASS ≥ 85%
- EVIDENCE_PASS ≥ 85%
- Latency < 250ms (dok-haku + mapping)

---

## 6) Mitä EI tehdä v9:ssä
- Ei LoRAa / fine-tuningia
- Ei LLM:llä automaattista faktagenerointia ilman dokumenttitodisteita
- Ei “täysin vapaa” analyysi ilman lain ja dokumentin linkkejä

---

## 7) Seuraava askel (nyt)
1) Valitse 1 tilinpäätös-PDF (Lapua, vuosi X) ja tuota siitä **structured JSON** (otsikot + sivut + taulukot)
2) Toteuta `build_document_graph.py` (3.1)
3) Rakenna dokumentti-indeksi (3.2)
4) Kirjoita 30 real-doc kysymystä (5) ja aja ensimmäinen baseline

