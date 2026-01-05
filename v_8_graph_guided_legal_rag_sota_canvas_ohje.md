# v8 – Graph-guided Legal RAG (SOTA) – Canvas-ohje

## Tavoite
Rakennetaan **täydellinen lakikokonaisuuden tulkintajärjestelmä**, joka yhdistää:
- nykyisen v7.2 **SOTA-retrieval-ytimen** (router + bge-m3 + Chroma per laki + deterministinen rerank)
- uuden **eksplisiittisen rakenteellisen lakigraafin** (nodes+edges)
- **graph-guided retrievalin**: vektori hakee, graafi laajentaa viittaukset/poikkeukset/määritelmät → muodostetaan normipolku

**Ei LoRAa. Ei LLM:ää retrieval-vaiheessa.**

---

## 0) Nykyinen ydin (pidetään ennallaan)
Perustuu end-to-end-dokumenttiin.
- Law Router (keyword-based) → top-2 law
- Embedding: BAAI/bge-m3 (normalize_embeddings=True)
- ChromaDB indeksit per laki (momentti node)
- Multi-law query → merge
- Deterministinen rerank: router bonus + pair guards + diversity rule
- Vastaus: top-1 momentin teksti (extractive)

v8 lisää graafikerroksen **tämän päälle**, ei tilalle.

---

## 1) Miksi graafi (uusi kulma)
Vektori löytää usein oikean pykälän, mutta ei automaattisesti:
- seuraa **viittausketjuja** ("kuten 12 §:ssä säädetään")
- nouda **poikkeuksia** ("poiketen 1 momentista")
- liitä **määritelmiä** ("tässä laissa tarkoitetaan")

Graafi tekee tästä determinististä ja testattavaa.

---

## 2) v8 Arkkitehtuuri (kerroksittain)

### Kerros A: Retrieval (v7.2)
- tuottaa candidate poolin (top-k)

### Kerros B: Structural Legal Graph (uusi)
- nodes + edges lakikokonaisuuden rakenteesta ja viittauksista

### Kerros C: Graph-guided Context Builder (uusi)
- laajentaa candidate poolin graafin avulla:
  - viitatut pykälät/momentit
  - poikkeukset
  - määritelmät

### Kerros D: Normipolku + perusteltu vastaus (extractive)
- palautetaan:
  - top-1 momentti
  - + “tukisolmut” (references/exceptions/definitions)
  - + polku: M0 → (ref/except/def) → M1 → ...

---

## 3) Graafiskeema (minimi)

### Node-tyypit
- `LAW` (laki)
- `SECTION` (pykälä)
- `MOMENT` (momentti)
- `DEFINITION` (määritelmäsolmu) [optionaalinen]

### Edge-tyypit (minimi)
- `HAS_SECTION`: LAW → SECTION
- `HAS_MOMENT`: SECTION → MOMENT
- `REFERS_TO`: MOMENT → MOMENT/SECTION (viittaus)
- `EXCEPTS`: MOMENT → MOMENT/SECTION (poikkeus)
- `DEFINES`: MOMENT → DEFINITION
- `DEFINED_IN`: DEFINITION → MOMENT

### Node-id standardi
- käytä nykyistä `node_id`-formaattia (esim. `410/2015:...:113:1`)

---

## 4) Graafin rakentaminen (deterministinen)

### 4.1 Lähdedata
- käytä teidän momentti-JSONL:ää (metadata + text + anchors)

### 4.2 Viittausparsinta (regex + säännöt)
Poimi lakitekstistä viittaukset:
- pykäläviitteet: `\b(\d+)\s*§\b`
- momenttiviitteet: `\b(\d+)\s*momentti\b` tai `\b(\d+)\s*mom\.\b`
- lain sisäinen viittaus: "tämän lain" → sama law_key
- lain ulkoinen viittaus: jos teksti sisältää toisen lain nimen (myöhemmin)

Tuota edge-lista:
- `REFERS_TO` jos löydetään viittaus
- `EXCEPTS` jos löydetään avainsanat: "poiketen", "poikkeuksena", "jollei"

### 4.3 Tallennusmuoto (valitse kevyt)
- Ensimmäinen versio: `graph/edges.jsonl` + `graph/nodes.jsonl`
- Myöhemmin: Neo4j / RDF / NetworkX / sqlite

---

## 5) Query-time: Graph-guided retrieval

### 5.1 Candidate pool
- aja nykyinen multi-law query → top-k (esim. k_total=10)

### 5.2 Graph expand (1–2 hop)
Kullekin top-hitille:
- hae naapurit:
  - `REFERS_TO` (viitatut)
  - `EXCEPTS` (poikkeukset)
  - `DEFINES/DEFINED_IN` (määritelmät)
- rajoita:
  - max_hops = 2
  - max_nodes_added = 10

### 5.3 Scoring graafin kautta
- perus: lisätyt solmut saavat `score = parent_score - decay`
  - decay esim. 0.05 per hop
- priorisoi:
  - EXCEPTS (poikkeukset) > REFERS_TO > DEFINITIONS

### 5.4 Lopputulos
- palauta:
  - `primary_hit` (top-1)
  - `supporting_nodes` (top N graph-expanded)
  - `path` (polku edges)

---

## 6) Vastausformaatti (uusi, mutta edelleen extractive)
Palauta aina:
- **Lähde (primary):** LAW § moment
- **Teksti:** primary momentin teksti
- **Normipolku:** lista (primary → ref/except/def)
- **Tukilähteet:** 2–5 tärkeintä laajennettua solmua (poikkeus/määritelmä)

Ei synteesiä ilman lähteitä.

---

## 7) Eval v8 (uusi “graph-needed” -setti)
Lisää uusi testipaketti, jossa oikea vastaus vaatii graafia:
- poikkeusketjut
- määritelmät
- viittausketjut (1–2 hop)

### Mittarit
- `GRAPH_PATH_PASS`: löytyykö oikea polku
- `PRIMARY_PASS`: top-1 oikein
- `SUPPORT_PASS`: poikkeus/määritelmä mukana top supportissa
- Latency-budjetti: < 150ms (graph expand oltava kevyt)

---

## 8) Toteutusjärjestys (commit-suunnitelma)
1) `v8: build structural graph (nodes+edges jsonl)`
2) `v8: graph query api (neighbors + hop limit)`
3) `v8: graph-guided context builder (expand + decay scoring)`
4) `v8: answer format with normipolku (extractive)`
5) `v8: add graph-needed eval set + metrics`

---

## 9) Do/Don’t (selkeät rajat)
### DO
- rakenna graafi deterministisesti
- pidä retrieval-ydin ennallaan
- tee graph expand rajatuksi ja nopeaksi
- lisää eval-setti, joka pakottaa graafihyödyn

### DON’T
- älä siirry LLM-rakennettuun KG:hen ilman QA:ta
- älä lisää cross-encoderia ennen kuin graph-needed eval näyttää tarpeen
- älä riko v7.2 gate-evalia

---

## 10) Seuraava askel (nyt)
1) Toteuta **graafin rakentaja**: `scripts/build_structural_legal_graph.py`
   - input: `laws/*/analysis_layer/json/*.jsonl`
   - output: `graph/nodes.jsonl`, `graph/edges.jsonl`
2) Tee pieni CLI:
   - `python scripts/graph_debug.py --node <node_id> --hops 2`
3) Aja 5 käsin valittua pykälää läpi ja varmista, että `REFERS_TO` ja `EXCEPTS` syntyvät.

