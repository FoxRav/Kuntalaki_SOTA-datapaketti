# v8.1 – GraphRAG-kovennus (PRIMARY/SUPPORT PASS) – Canvas-ohje

## Tavoite (v8.1)
Nostetaan v8-graafikerroksen mittarit vähintään:
- **PRIMARY_PASS ≥ 90%** (min 80% gate)
- **SUPPORT_PASS ≥ 80%** (min 60% gate)
- **GRAPH_PATH_PASS ≥ 85%**
- **Latency < 150ms**

v7.2 retrieval (STRICT/ROUTING/HN) pidetään koskemattomana.

---

## 1) Juurisyyt (v8 havaintoihin perustuva)
Ongelmat näkyvät kahdessa kohdassa:
1) **Wrong law / wrong primary**: router ei aina priorisoi oikein (esim. "kunnan")
2) **Support-solmut puuttuvat**: poikkeus/määritelmä ei päädy supporting-listaan vaikka edge löytyy

---

## 2) v8.1 Muutokset (yksi muutos per commit)

### 2.1 Router-kovennus (ennen retrievalia)
**Tavoite:** vähennä väärään lakiin reititystä, joka romahduttaa PRIMARY_PASS.

Toteutus:
- Lisää routeriin vahvempi "kunta"-klusteri:
  - terms: `kunta`, `kunnan`, `kuntakonserni`, `kuntalaki`, `valtuusto`, `kunnanhallitus`, `tarkastuslautakunta`
  - effect: kuntalaki weight +1.0 (ennen normalisointia)
- Lisää termitilanne: jos query sisältää `kunnan` tai `kuntakonserni`, **pakota** Kuntalaki top-2 listaan

Commit: `v8.1: harden router for municipal context`

---

### 2.2 Rerank: “law-mismatch penalty” (vain kun query sisältää vahvan ankkurin)
**Tavoite:** estä geneerinen KPL/KPA osuma voittamasta kun query kertoo kuntakontekstin.

Toteutus:
- Lisää sääntö (ennen final sorttia):
  - jos query sisältää `kunnan|kunta|kuntakonserni` ja hit.law_key != KUNTA → `score -= 0.03`
- Tee parametriseksi: `LAW_MISMATCH_PENALTY = 0.03`

Commit: `v8.1: add law mismatch penalty for municipal anchors`

---

### 2.3 Viittausparsinnan tarkennus (momentti- vs pykälätaso)
**Tavoite:** parantaa GRAPH_PATH_PASS ja SUPPORT_PASS.

Toteutus:
- Lisää parseriin tuki muodoille:
  1) `X §:n Y momentissa` → edge MOMENT->MOMENT
  2) `X §:ssä` → MOMENT->SECTION (jos momentti ei tiedossa)
  3) `N luvun M §` → map chapter+section (jos chapter metadata saatavilla)
- Lisää normalisointi suomen taivutuksille: `§:n`, `§ssä`, `§ssä`, `§:ään`

Commit: `v8.1: improve reference parsing (section vs moment)`

---

### 2.4 Support-budget: pakotetut kategoriat (EXCEPTS + DEFINES)
**Tavoite:** SUPPORT_PASS ylös; nykyinen prioriteetti ei takaa kattavuutta.

Toteutus:
- Rakenna supporting-nodelista 2-vaiheisesti:
  1) **pakolliset**:
     - jos löytyy EXCEPTS 1–2 hopissa → ota paras EXCEPTS
     - jos query sisältää (määritelmä|tarkoitetaan|tässä laissa) ja löytyy DEFINES → ota paras DEFINES
  2) täydennä loput pistejärjestyksellä (EXCEPTS > REFERS_TO > DEFINES)
- Parametrit:
  - `SUPPORT_MAX = 5`
  - `HOPS_MAX = 2`
  - `DECAY_PER_HOP = 0.05`

Commit: `v8.1: enforce support budget (excepts/defines)`

---

### 2.5 Graph-eval: “golden path” (tiukempi totuus)
**Tavoite:** varmistaa, että mittari ohjaa oikeaan korjaukseen.

Toteutus:
- Laajenna `questions_graph_needed.json` skeemaa:
  - `expected_primary_node_id`
  - `expected_edges`: lista (edge_type, target_node_id)
  - `expected_support_any`: lista node_id:itä joista vähintään 1 pitää löytyä supportissa
- Päivitä eval:
  - PRIMARY_PASS: primary node_id match
  - GRAPH_PATH_PASS: polku sisältää vähintään yhden expected edge
  - SUPPORT_PASS: support sisältää expected_support_any

Commit: `v8.1: add golden path expectations to graph eval`

---

## 3) Ajoprotokolla (pakollinen)
Jokaisen commitin jälkeen:
1) `python scripts/run_graph_eval.py` (graph-needed)
2) tallenna raportti: `reports/v8_1_graph_eval_<commit>.md`
3) regressiosääntö:
   - jos latency > 150ms → revert tai optimoi hops/support/candidates

---

## 4) Optimointikytkimet (jos latency nousee)
- pienennä `SUPPORT_MAX`
- pienennä `HOPS_MAX` (2 → 1)
- nosta `MIN_SCORE` retrievalissa
- rajaa graph expand vain top-3 primary-candidateen

---

## 5) Definition/Exception-heuristiikat (domain-säännöt)
- EXCEPTS triggerit: `poiketen`, `poikkeuksena`, `jollei`, `ellei`, `siitä huolimatta`
- DEFINES triggerit: `tarkoitetaan`, `tässä laissa`, `määritelmä`, `on`

---

## 6) Lopputavoite: v8.1 PASS
Kun kaikki tavoitteet täyttyvät:
- päivitä `graph/README.md` mittareilla
- päivitä pää-README
- taggaa `v8.1.0`

---

## 7) Seuraava askel (nyt)
1) Tee **router-kovennus** (2.1) ja aja graph-eval.
2) Tee **support-budget** (2.4) ja aja graph-eval.
3) Tee **parser-tarkennus** (2.3) ja aja graph-eval.
4) Lisää **golden path** -skeema (2.5) viimeisenä.

