# Kuntalaki RAG – Jatkokehitys v4 (Cursor Canvas)

Tämä on **ajettava työlista**. Tee vaiheet järjestyksessä. Älä muuta laatuportteja.

---

## TAVOITE v4

Nostetaan nämä portit PASS-tilaan:
- Gate 2: SHOULD ≥ 95%
- Gate 3: toimintakertomus ≥ 90%
- Gate 4: hard negatives = 0

Pidä jo saavutettu:
- MUST 100%
- MUST Top-1 ≥ 80%

---

## VAIHE 0 – LUKITSE TESTIT (ei drift)

1) Tee branch: `feature/v4-anchors-pairguards`
2) Lukitse eval-input:
- `eval/v3/questions_kuntalaki_v3.json` ei muutu muualla kuin dokumentoidussa “test-bug fix” commitissa.
3) Lisää `eval/v3/CHANGELOG.md`:
- kirjaa jokainen muutos kysymyssettiin (ID + syy + viittaus lakitekstiin)

---

## VAIHE 1 – ANCHORS-KENTTÄ (momentti-disambiguointi)

### 1.1 Lisää `anchors[]` JSONL:ään
Muokkaa `analysis_layer/build_kuntalaki_json.py`:

- lisää jokaiselle momentille: `anchors: list[str]`
- `anchors` ovat **momenttispesifejä avaintermejä** (ei sama lista kaikille)

Pakollinen §115-anchors:
- 115:1 anchors:
  - `sisäinen valvonta`
  - `riskienhallinta`
  - `tavoitteiden toteutuminen`
  - `tuleva kehitys`
- 115:2 anchors:
  - `alijäämä`
  - `alijäämän kattaminen`
  - `kattamistoimenpiteet`
  - `talouden tasapainottaminen`
- 115:3 anchors:
  - `tuloksen käsittely`
  - `tuloskäsittelyesitys`
  - `tilikauden tulos`

Lisäksi lisää §110/110a ja §113/§114 ankkurit:
- 110a anchors: `covid`, `korona`, `pandemia`, `poikkeus`
- 114 anchors: `konserni`, `konsernitilinpäätös`, `kuntakonserni`

### 1.2 Validointi
Luo/ajaa tarkistus: `analysis_layer/tests/test_anchors.py`
- assert: kaikilla §115 momenteilla anchors != []
- assert: anchors-listat eivät ole identtiset keskenään

---

## VAIHE 2 – ANCHOR-OVERLAP RERANK (deterministinen)

### 2.1 Toteuta overlap
Muokkaa/luo `analysis_layer/query_boost.py`:

- jos hitin `section_num == "115"` → laske overlap(query_terms, anchors)
- score += 0.01 * overlap_count (cap +0.05)

Query-terms normalisointi:
- lowercase
- poista välimerkit
- split whitespace

### 2.2 Aktivointiehto
Suorita overlap vain jos query sisältää jonkin:
- `valvonta`, `riski`, `riskienhallinta`, `alijäämä`, `kattam`, `tuloskäsittely`, `konserni`

---

## VAIHE 3 – PAIR-GUARDS (hard negatives = 0)

Lisää `PAIR_GUARDS`-taulu `analysis_layer/query_boost.py`:

1) 113 vs 114
- if query contains `konserni` → boost 114, penalize 113
- if query contains `tilinpäätös` and NOT `konserni` → boost 113, penalize 114

2) 110 vs 110a
- if query contains (`covid` OR `korona` OR `pandemia`) → boost 110a, penalize 110

3) 62 vs 62a/62b (jos mukana evalissa)
- if query contains `yhdistyminen` OR `jakautuminen` → penalize 62 (eroaminen)

Vaikutus:
- boost +0.03…+0.05
- penalize -0.03…-0.05

Pakollinen sääntö:
- jos penalize pudottaa score alle 0 → clamp to 0

---

## VAIHE 4 – TESTIDATA-BUGIT (vain perustellut)

### 4.1 KL-SHOULD-051 korjaus
Etsi `KL-SHOULD-051`:
- jos kysymys ei vastaa lakitekstiä → korjaa muotoilu.
- lisää `notes` kenttään viite: “miksi korjattu”.

Älä muuta muita kysymyksiä ilman syytä.

---

## VAIHE 5 – REBUILD / REINDEX / EVAL

Aja aina samat komennot:

1) rebuild json/jsonl
2) rebuild index
3) eval matrix:
- k=10, min_score=0.50
- k=5, min_score=0.55
- k=3, min_score=0.60

Tuota:
- `eval/v3/report_matrix.md`
- `eval/v3/kuntalaki_eval_v3_results.json`

---

## VAIHE 6 – HYVÄKSYMISKUNTO (merge-gate)

Merge sallitaan vain jos:
- Gate 2 PASS (SHOULD ≥ 95%)
- Gate 3 PASS (toimintakertomus ≥ 90%)
- Gate 4 PASS (hard negatives = 0)

Jos jokin failaa:
- aja `analyze_fails.py`
- listaa fail-ID:t ja syy (väärä pykälä / väärä momentti / score)
- korjaa ensisijaisesti anchors/pair-guards

---

## LOPPUOHJE

Tämä on retrieval-järjestelmän tuotantokelpoisuuden varmistus.
Älä lisää LLM:iä retrievaliin.
Älä säädä laatuportteja.
Tee pienet muutokset ja mittaa joka kerta.

