# Kuntalaki RAG – Jatkotoimet (Cursor AI / v4)

## 0) Nykytila (matrix-eval)
**Paras konfiguraatio gatejen kannalta:** `k=10`, `min_score=0.50`
- TOTAL ~97.3%
- MUST 100%
- SHOULD ~97.2% (Gate 2 läpi)
- Top-1 ~84.7%
- Latency ~47 ms

**Huomio:** `k=3, min_score=0.50` antaa hieman paremman Top-1 (~85.3%), mutta kokonaispassi heikompi (~94.0%).

**TÄMÄN HETKEN “SAFE DEFAULT” (prod / main):** `k=10`, `min_score=0.50`

---

## 1) Tavoite v4
Nosta **Top-1 / precision@1** ilman että SHOULD-pass rate laskee alle 95% tai hard negatives rikkoutuu.

Laatuportit (pidä ennallaan):
- Gate 1: MUST ≥ 99%
- Gate 1b: MUST Top-1 ≥ 80%
- Gate 2: SHOULD ≥ 95%
- Gate 4: hard negatives = 0
- Gate 5: latency < 150 ms

---

## 2) Työjärjestys (tee näin)

### Vaihe A — Lukitse baseline
1. Varmista, että eval ajetaan aina myös baseline-konfigilla:
   - `k=10` + `min_score=0.50`
2. Lisää raporteihin selkeä “baseline summary” -osio.

### Vaihe B — Implementoi anchors[] dataan (momenttitaso)
Tavoite: lisätä jokaiselle momentille ankkurilista (lakitekstistä poimitut avainsanat), esim.
- §115:1: `sisäinen valvonta`, `riskienhallinta`, `tavoitteiden toteutuminen`
- §115:2: `alijäämä`, `alijäämän kattaminen`, `tasapainottaminen`
- §115:3: `tuloksen käsittely`, `tuloskäsittelyesitys`

Tehtävät:
1. Lisää JSON-tuotantoon kenttä: `anchors: string[]` momentin metadataan.
2. Varmista, että anchors tulee mukaan indeksin dokumenttitekstiin tai metadataan (sen mukaan miten scorer toimii).
3. Rebuild data + reindex.

### Vaihe C — Anchor-overlap rerank (query-time)
Tavoite: pieni deterministinen lisäscore vain silloin kun disambiguointi on relevanttia.

Rerank-sääntö (suositus):
- Laske `overlap = count(match(query_terms, anchors))`
- `score += 0.01 * overlap`, cap `+0.05`

Rajaus (ettei sotke muuta):
- Aktivoi vain, jos top-N sisältää samoja pykäliä eri momenteilla **tai** jos query sisältää “momentti-signaaleja” (esim. alijäämä, riskienhallinta, konserni, covid).

### Vaihe D — Pair-guards (hard-negative varmistus)
Deterministiset säännöt lähisekaantumisiin:
- `konserni` → boost 114, penalize 113
- `tilinpäätös` ilman konsernia → boost 113
- `covid`/`korona` → boost 110a, penalize 110

Pidä vaikutus pieni (esim. +/- max 5%) ja dokumentoi logiin, että guard triggaa.

### Vaihe E — Aja matrix-eval uudelleen ja vertaile
1. Aja matrix-eval samoilla matriisiparametreilla.
2. Vertaile erityisesti:
   - baseline: `k=10, min_score=0.50`
   - top-1, precision@1
   - hard_negative_violations
   - latency

---

## 3) Konkreettinen TODO-lista Cursorille

### Data
- [ ] Lisää `anchors[]` momentti-jsoniin (tuotantopipeline)
- [ ] Lisää yksikkötesti: anchors-kenttä ei tyhjä niissä momenteissa joissa disambiguointi tunnetusti vaikea (115, 110/110a, 113/114)

### Retrieval
- [ ] Lisää `anchor_overlap_rerank(query, hits)` (capattu, deterministinen)
- [ ] Lisää `pair_guard_adjust(query, hits)`
- [ ] Lisää debug-log: mitkä säännöt triggasivat ja paljonko score muuttui

### Eval
- [ ] Aja: `run_kuntalaki_eval_v3.py` / matrix-run
- [ ] Generoi raportti: baseline vs v4 (delta-taulukko)

---

## 4) Hyväksymiskriteerit (merge)
- [ ] Baseline-konfig (`k=10, min_score=0.50`) pysyy vähintään:
  - SHOULD ≥ 95%
  - MUST = 100% (tai vähintään 99%)
  - hard_negative_violations = 0
- [ ] Top-1 / precision@1 paranee **tai** pysyy samana ilman muiden porttien regressiota
- [ ] Latency pysyy < 150 ms

---

## 5) Nopein “ensimmäinen testipyyhkäisy”
1) Implementoi vain pair-guards → reindex ei pakollinen (query-time)
2) Aja baseline-eval + matrix
3) Implementoi anchors + overlap-rerank → reindex tarvitaan
4) Aja matrix uudelleen

---

## 6) Muistutus
- Älä “fixaa” laatua muuttamalla min_scorea ylöspäin (heikentää SHOULD-passia nopeasti).
- Käytä `k=10, min_score=0.50` lähtökohtana ja tee Top-1-parannukset rerank/guards/anchors -kerroksilla.

