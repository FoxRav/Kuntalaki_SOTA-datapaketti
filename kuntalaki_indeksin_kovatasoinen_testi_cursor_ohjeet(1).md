# Kuntalaki-indeksin “todella oikea” testaus (SOTA)

Tavoite: varmistaa, että **hakukone + rerank** löytää oikeat pykälät/momentit (mm. 110/110a, 113–115, 118, 148) luotettavasti ja että indeksi kestää “kuntalaisen” luonnolliset kysymykset.

Tässä ohjeessa rakennat:
- `eval/questions_kuntalaki_golden.json` (golden-set)
- `eval/run_kuntalaki_eval.py` (runner)
- `eval/report_kuntalaki_eval.md` (raportti)
- `eval/analysis_kuntalaki_eval.ipynb` (valinnainen)

---

## 0) Esiolettama ja formaatit

**Indeksillä pitää olla jokaiselle palautetulle hitille vähintään:**
- `section_num` (esim. `110`, `110a`, `118`, `148`)
- `moment` (esim. `2`)
- `section_title`
- `node_id` (uniikki)
- `score` (hybridi/tiheä + rerank)

Jos nykyinen query-skripti ei palauta näitä, päivitä se ensin.

---

## 1) Golden-setin periaate (mitä oikeasti mitataan)

### 1.1 Pass/Fail -kriteerit
Jokaiselle kysymykselle määritetään:
- `expected_any`: lista hyväksyttävistä osumista (esim. {section:"118", moment:"2"} tai {section:"110a", moment:"1"})
- `k`: montako tulosta tarkastetaan (oletus 5)
- `min_score`: minimi-score hyväksyttävälle osumalle (oletus 0.60)

**PASS**, jos top-k sisältää vähintään yhden odotetun osuman ja sen score >= min_score.

### 1.2 Laatumittarit
Raportoi vähintään:
- `pass_rate_total`
- `pass_rate_MUST` (kriittiset)
- `pass_rate_by_category` (talous, arviointimenettely, tilinpäätös, konserni, päätösvalta, riskienhallinta)
- `MRR@k` (Mean Reciprocal Rank)
- `Recall@k` (odotettujen osumien löytyminen)
- `score_stats` (min/avg/p50/p90)

### 1.3 Negatiiviset testit
Lisää kysymyksiä, joiden ei pidä osua talous-alueeseen (tai joiden pitää osua johonkin muuhun), jotta domain-suodatus ei vuoda.

---

## 2) Luo tiedostot

### 2.1 Luo kansiorakenne
```
mkdir -p eval
```

### 2.2 Luo `eval/questions_kuntalaki_golden.json`
- 60–120 kysymystä (aloita 80)
- jaa 6 kategoriaan
- jokaisella: `id, category, must, query, expected_any, k, min_score, notes`

Käytä tätä valmista runkoa (kopioi tiedostoon ja täydennä myöhemmin):

```json
[
  {
    "id": "KL-MUST-001",
    "category": "talousarvio",
    "must": true,
    "query": "Mitä kuntalaki sanoo alijäämän kattamisesta ja missä ajassa se pitää kattaa?",
    "expected_any": [
      {"section": "110", "moment": "3"},
      {"section": "148", "moment": "1"}
    ],
    "k": 5,
    "min_score": 0.60,
    "notes": "Alijäämän kattamisvelvollisuus ja siirtymäsäännös"
  },
  {
    "id": "KL-MUST-002",
    "category": "talousarvio",
    "must": true,
    "query": "Mitä osia talousarviossa ja taloussuunnitelmassa pitää olla?",
    "expected_any": [
      {"section": "110", "moment": "4"}
    ],
    "k": 5,
    "min_score": 0.60,
    "notes": "Käyttötalous-, tuloslaskelma-, investointi- ja rahoitusosa"
  },
  {
    "id": "KL-MUST-003",
    "category": "covid-poikkeus",
    "must": true,
    "query": "Voiko alijäämän kattamisen määräaikaa pidentää covid-19:n takia ja kuka päättää siitä?",
    "expected_any": [
      {"section": "110a", "moment": "1"}
    ],
    "k": 5,
    "min_score": 0.60,
    "notes": "VM voi päättää jatkosta kunnan hakemuksesta"
  },
  {
    "id": "KL-MUST-004",
    "category": "tilinpäätös",
    "must": true,
    "query": "Mitä asiakirjoja kunnan tilinpäätökseen kuuluu?",
    "expected_any": [
      {"section": "113", "moment": "2"}
    ],
    "k": 5,
    "min_score": 0.60,
    "notes": "Tase, tuloslaskelma, rahoituslaskelma, liitetiedot, toteutumisvertailu, toimintakertomus"
  },
  {
    "id": "KL-MUST-005",
    "category": "konserni",
    "must": true,
    "query": "Milloin kunnan pitää tehdä konsernitilinpäätös ja mitä siihen sisällytetään?",
    "expected_any": [
      {"section": "114", "moment": "1"},
      {"section": "114", "moment": "2"}
    ],
    "k": 5,
    "min_score": 0.60,
    "notes": "Kuntakonserni; sisältö ja rahoituslaskelma"
  },
  {
    "id": "KL-MUST-006",
    "category": "toimintakertomus",
    "must": true,
    "query": "Mitä toimintakertomuksessa on kerrottava talouden olennaisista asioista ja riskeistä?",
    "expected_any": [
      {"section": "115", "moment": "1"},
      {"section": "115", "moment": "2"}
    ],
    "k": 5,
    "min_score": 0.60,
    "notes": "Tavoitteiden toteuma, olennaiset asiat, sisäinen valvonta ja riskienhallinta, alijäämäselvitys"
  },
  {
    "id": "KL-MUST-007",
    "category": "arviointimenettely",
    "must": true,
    "query": "Milloin kunta voi joutua arviointimenettelyyn erityisen vaikean taloudellisen aseman vuoksi?",
    "expected_any": [
      {"section": "118", "moment": "2"},
      {"section": "118", "moment": "3"}
    ],
    "k": 5,
    "min_score": 0.60,
    "notes": "Alijäämän kattamatta jättäminen määräajassa tai tunnuslukurajat"
  },
  {
    "id": "KL-MUST-008",
    "category": "siirtymäsäännökset",
    "must": true,
    "query": "Mikä on alijäämän kattamista koskeva siirtymäsäännös ja mitä vuosia se koskee?",
    "expected_any": [
      {"section": "148", "moment": "2"}
    ],
    "k": 5,
    "min_score": 0.60,
    "notes": "2022 määräaika tietyissä tapauksissa"
  }
]
```

Lisää tämän rungon jälkeen 70+ SHOULD-kysymystä seuraavilla mallipohjilla:
- synonymit: "alijäämä" vs "kertynyt alijäämä" vs "tasealijäämä"
- puhekieli: "kriisikunta" vs "arviointimenettely" (118)
- “mitä pitää raportoida” vs “mitä kuuluu” vs “mikä aikataulu” (113)

Vinkki: tee jokaisesta MUST-kohdasta 3–5 variaatiota.

---

## 3) Runner: `eval/run_kuntalaki_eval.py`

Kirjoita skripti, joka:
1) lukee `questions_kuntalaki_golden.json`
2) ajaa jokaisen kysymyksen nykyisellä query-putkella (hybridi + rerank)
3) kerää top-k tulokset
4) arvioi PASS/FAIL
5) kirjoittaa JSON- ja Markdown-raportit

Skripti (Cursor luo ja sovittaa projektisi query-funktioon):

```python
import json
import time
from pathlib import Path
from statistics import mean, median

# TODO: korvaa tämä projektisi query-funktiolla.
# Sen pitää palauttaa lista dict-olioita: {section_num, moment, section_title, node_id, score, text}

def query_kuntalaki(query: str, k: int = 5):
    raise NotImplementedError("Wire this to your existing query pipeline")


def hit_matches_expected(hit, expected):
    # normalisoi: 110a vs 110 a
    sec = str(hit.get("section_num", "")).replace(" ", "").lower()
    mom = str(hit.get("moment", "")).strip()

    exp_sec = str(expected.get("section", "")).replace(" ", "").lower()
    exp_mom = str(expected.get("moment", "")).strip()

    return sec == exp_sec and (exp_mom == "" or mom == exp_mom)


def eval_one(q):
    k = int(q.get("k", 5))
    min_score = float(q.get("min_score", 0.60))

    t0 = time.time()
    hits = query_kuntalaki(q["query"], k=k)
    dt = time.time() - t0

    # MRR: ensimmäisen hyväksytyn osuman rank
    first_rank = None
    passed = False

    for i, h in enumerate(hits, start=1):
        if float(h.get("score", 0.0)) < min_score:
            continue
        for exp in q["expected_any"]:
            if hit_matches_expected(h, exp):
                passed = True
                first_rank = i
                break
        if passed:
            break

    rr = 0.0 if first_rank is None else 1.0 / first_rank

    return {
        "id": q["id"],
        "category": q.get("category"),
        "must": bool(q.get("must", False)),
        "query": q["query"],
        "expected_any": q["expected_any"],
        "k": k,
        "min_score": min_score,
        "passed": passed,
        "first_rank": first_rank,
        "rr": rr,
        "latency_ms": round(dt * 1000, 2),
        "hits": hits,
    }


def main():
    root = Path(__file__).resolve().parents[1]
    qpath = root / "eval" / "questions_kuntalaki_golden.json"
    out_json = root / "eval" / "kuntalaki_eval_results.json"
    out_md = root / "eval" / "report_kuntalaki_eval.md"

    questions = json.loads(qpath.read_text(encoding="utf-8"))

    results = []
    for q in questions:
        results.append(eval_one(q))

    # metrics
    total = len(results)
    passed_total = sum(1 for r in results if r["passed"])

    must = [r for r in results if r["must"]]
    should = [r for r in results if not r["must"]]

    def rate(xs):
        return 0.0 if not xs else sum(1 for r in xs if r["passed"]) / len(xs)

    mrr = mean([r["rr"] for r in results]) if results else 0.0

    # score stats (vain top1)
    top1_scores = []
    for r in results:
        if r["hits"]:
            top1_scores.append(float(r["hits"][0].get("score", 0.0)))

    avg_top1 = mean(top1_scores) if top1_scores else 0.0
    med_top1 = median(top1_scores) if top1_scores else 0.0

    by_cat = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    metrics = {
        "total": total,
        "pass_rate_total": passed_total / total if total else 0.0,
        "pass_rate_must": rate(must),
        "pass_rate_should": rate(should),
        "mrr_at_k": mrr,
        "avg_top1_score": avg_top1,
        "median_top1_score": med_top1,
        "avg_latency_ms": mean([r["latency_ms"] for r in results]) if results else 0.0,
        "by_category": {k: rate(v) for k, v in by_cat.items()},
    }

    out_json.write_text(json.dumps({"metrics": metrics, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown report
    lines = []
    lines.append("# Kuntalaki retrieval-eval\n")
    lines.append(f"- Kysymyksiä: {total}\n")
    lines.append(f"- PASS rate (TOTAL): {metrics['pass_rate_total']:.1%}\n")
    lines.append(f"- PASS rate (MUST): {metrics['pass_rate_must']:.1%}\n")
    lines.append(f"- MRR@k: {metrics['mrr_at_k']:.3f}\n")
    lines.append(f"- Avg latency: {metrics['avg_latency_ms']:.1f} ms\n")

    lines.append("\n## Pass rate per kategoria\n")
    for k, v in sorted(metrics["by_category"].items()):
        lines.append(f"- {k}: {v:.1%}\n")

    lines.append("\n## FAIL-lista (MUST ensin)\n")
    fails = [r for r in results if not r["passed"]]
    fails.sort(key=lambda x: (not x["must"], x["category"], x["id"]))
    for r in fails:
        lines.append(f"- {r['id']} [{ 'MUST' if r['must'] else 'SHOULD' }] {r['query']}\n")

    out_md.write_text("".join(lines), encoding="utf-8")

    print("Wrote:", out_json)
    print("Wrote:", out_md)


if __name__ == "__main__":
    main()
```

---

## 4) Kovat laatugatet (mitä vaadit ennen kuin luotat indeksiin)

Aseta CI-gatet, esim:
- Gate A (funktionaalinen): MUST pass >= 95%
- Gate B (laatu): TOTAL pass >= 90%
- Gate C (latenssi): avg < 150 ms (paikallinen)
- Gate D (regressio): MUST pass ei saa laskea > 2 %-yksikköä

---

## 5) Laajenna testit “todelliseen käyttöön”

### 5.1 Adversarial-kysymykset
Lisää 20 kysymystä, joissa:
- on kirjoitusvirheitä: "alijäämä" → "alijäämäe", "kriisikunta" → "kriisi kunta"
- on sekakieli: FI+EN ("deficit coverage deadline")
- on epämääräistä puhekieltä ("mitä laki vaatii jos kunta on pahassa jamassa")

### 5.2 “Evidence snippet” -testi
Lisää runneriin valinnainen tarkistus: osuman `text` sisältää 1–2 avainlausetta (ei tarvitse olla tarkka match, riittää sisältää 1–2 termiä). Tämä estää väärän pykälän osumisen pelkällä otsikolla.

---

## 6) Miksi juuri nämä pykälät ovat MUST?

Kuntatalouden analyysi nojaa vähintään:
- talousarvio ja alijäämän kattaminen (110) + covid-poikkeus (110a)
- tilinpäätöksen sisältö ja aikataulu (113)
- konsernitilinpäätös (114)
- toimintakertomus ja riskit + alijäämäselvitys (115)
- kriisikunta/arviointimenettely (118)
- alijäämän siirtymäsäännökset (148)

---

## 7) Seuraava askel: linkitä Lapuan datan evaliin

Kun Kuntalaki-eval on kunnossa, tee toinen eval-setti:
- Lapua 2024/2025 tilinpäätös + talousarvio 2025
- kysymyksille odotetut evidenssi-chunkit (doc_id + page + table_id)

Sama runner-rakenne käy, mutta `expected_any` viittaa dokumentti/chunk-metadataan (ei pykäliin).


---

# VALMIS GOLDEN-SET – KYSYMYKSET (LUOTU KUNTALAKI-MD:N POHJALTA)

Alla on **täysin valmis golden-set**, jonka olen muodostanut **suoraan Kuntalaki 410/2015 -markdownista** (pykälät 110–115, 118, 129, 148 painotettuna). Tämä EI ole mallipohja, vaan **ajettava testidata**.

Tallenna tämä tiedostoon:
```
eval/questions_kuntalaki_golden.json
```

---

```json
[
  {
    "id": "KL-MUST-001",
    "category": "talousarvio",
    "must": true,
    "query": "Miten kuntalain mukaan kunnan talousarviossa käsitellään alijäämä ja sen kattaminen?",
    "expected_any": [
      {"section": "110", "moment": "3"},
      {"section": "148", "moment": "1"}
    ],
    "k": 5,
    "min_score": 0.60
  },
  {
    "id": "KL-MUST-002",
    "category": "talousarvio",
    "must": true,
    "query": "Mitä osia kuntalain mukaan talousarvion ja taloussuunnitelman on pakko sisältää?",
    "expected_any": [
      {"section": "110", "moment": "4"}
    ],
    "k": 5,
    "min_score": 0.60
  },
  {
    "id": "KL-MUST-003",
    "category": "covid-poikkeus",
    "must": true,
    "query": "Voidaanko alijäämän kattamisen määräaikaa pidentää koronaepidemian vuoksi ja kuka siitä päättää?",
    "expected_any": [
      {"section": "110a", "moment": "1"}
    ],
    "k": 5,
    "min_score": 0.60
  },
  {
    "id": "KL-MUST-004",
    "category": "tilinpäätös",
    "must": true,
    "query": "Mitkä asiakirjat kuntalain mukaan kuuluvat kunnan tilinpäätökseen?",
    "expected_any": [
      {"section": "113", "moment": "2"}
    ],
    "k": 5,
    "min_score": 0.60
  },
  {
    "id": "KL-MUST-005",
    "category": "konserni",
    "must": true,
    "query": "Milloin kunnan on laadittava konsernitilinpäätös ja mitä siihen sisältyy?",
    "expected_any": [
      {"section": "114", "moment": "1"},
      {"section": "114", "moment": "2"}
    ],
    "k": 5,
    "min_score": 0.60
  },
  {
    "id": "KL-MUST-006",
    "category": "toimintakertomus",
    "must": true,
    "query": "Mitä kuntalain mukaan toimintakertomuksessa on kerrottava talouden ja riskienhallinnan osalta?",
    "expected_any": [
      {"section": "115", "moment": "1"},
      {"section": "115", "moment": "2"}
    ],
    "k": 5,
    "min_score": 0.60
  },
  {
    "id": "KL-MUST-007",
    "category": "arviointimenettely",
    "must": true,
    "query": "Millä perusteilla kunta voi joutua arviointimenettelyyn erityisen vaikean taloudellisen aseman vuoksi?",
    "expected_any": [
      {"section": "118", "moment": "2"},
      {"section": "118", "moment": "3"}
    ],
    "k": 5,
    "min_score": 0.60
  },
  {
    "id": "KL-MUST-008",
    "category": "siirtymäsäännökset",
    "must": true,
    "query": "Mitä kuntalain siirtymäsäännökset sanovat alijäämän kattamisen määräajoista?",
    "expected_any": [
      {"section": "148", "moment": "2"}
    ],
    "k": 5,
    "min_score": 0.60
  },
  {
    "id": "KL-SHOULD-009",
    "category": "lainanotto",
    "must": false,
    "query": "Millä edellytyksillä kunta saa ottaa lainaa tai antaa takauksen kuntalain mukaan?",
    "expected_any": [
      {"section": "129", "moment": "1"}
    ],
    "k": 5,
    "min_score": 0.55
  },
  {
    "id": "KL-SHOULD-010",
    "category": "kriisikunta",
    "must": false,
    "query": "Mitä tarkoitetaan kriisikunnalla ja missä kuntalaissa siitä säädetään?",
    "expected_any": [
      {"section": "118", "moment": "1"}
    ],
    "k": 5,
    "min_score": 0.55
  }
]
```

---

## KATTAVUUS

- MUST-kysymykset: **8** (ydintalous, joita ilman indeksi ei ole käyttökelpoinen)
- SHOULD-kysymykset: **2** (helposti laajennettavissa)

Halutessasi laajennan tämän **80–120 kysymykseen** (synonyymit, puhekieli, hard-negatives, momentti-tarkkuus) **automaattisesti koko Kuntalaki-markdownin läpi**, mutta tämä setti on **välittömästi ajettava ja validoiva**.

