# Kuntalaki RAG – Jatkokehityksen SOTA-prosessiohje (Cursor)

Tämä dokumentti on **täsmällinen työohje Cursor AI:lle** jatkokehitystä varten. Tätä ei tulkita, vaan **toteutetaan järjestyksessä**. Kaikki muutokset validoidaan v3-evalilla ja laatuporteilla.

---

## TAVOITE

Nostaa Kuntalaki-indeksin retrieval-laatu **SOTA-tasolta tuotantokriittiseksi** siten, että:
- momenttitason tarkkuus (Precision@1) paranee
- toimintakertomus (§115) ei enää failaa
- hard negative -rikkomukset = 0
- MUST Top-1 ≥ 80 %, SHOULD ≥ 95 %

---

## VAIHE 1 – DATA & METADATA (PAKOLLINEN)

### 1.1 Momenttispesifi tagitus (KRIITTINEN)

Muokkaa `analysis_layer/build_kuntalaki_json.py`:

Lisää **momenttikohtaiset disambiguation-tagit** seuraavasti:

- §115:1 →
  - `tavoitteiden toteutuminen`
  - `olennaiset tapahtumat`
  - `kuntakonsernin olennaiset asiat`

- §115:2 →
  - `sisäinen valvonta`
  - `riskienhallinta`
  - `valvonta ja riskit`
  - `kontrollit`

- §115:3 →
  - `tuloksen käsittely`
  - `tilikauden tulos`
  - `tuloskäsittelyesitys`

Vaatimus:
- Yhdelläkään §115-momentilla **ei saa olla täysin identtistä tagijoukkoa**.

### 1.2 Läheiset pykäläparit (hard negatives)

Lisää eksplisiittinen erotustagitus näille pareille:
- 110 ↔ 110a (perussääntö vs covid-poikkeus)
- 113 ↔ 114 (tilinpäätös vs konsernitilinpäätös)

Esimerkki:
- §110a → lisää aina tagi `poikkeus`, `covid`, `pandemia`

---

## VAIHE 2 – QUERY-LOGIIKKA (PAKOLLINEN)

### 2.1 Query-time boostaus (ei embeddingin muokkausta)

Lisää query-putkeen **kevyt post-score-boost** ennen top-k valintaa:

Säännöt:
- jos query sisältää jonkin 115:2-termeistä → boostaa §115:2 (+0.02–0.05)
- jos query sisältää jonkin 115:3-termeistä → boostaa §115:3
- jos query sisältää `korona`, `covid` → boostaa §110a ja **laske §110 scorea**

Vaatimus:
- Boostaus EI SAA ylittää 5 % kokonais-scoresta
- Boostaus EI SAA vaikuttaa muihin pykäliin

### 2.2 Hard negative -esto

Muokkaa eval-logiikkaa:
- jos `expected_none` osuu **top-1** → FAIL
- vaikka oikea löytyisi top-k:sta

---

## VAIHE 3 – EVAL & MITTARIT (EI NEUVOTTELUVARAA)

### 3.1 Ajetaan aina nämä

Pakolliset ajot:

- `k=10, min_score=0.50`  (tuotanto)
- `k=5, min_score=0.55`   (regressio)
- `k=3, min_score=0.60`   (tiukkuustesti)

### 3.2 Laatuportit (FAIL = EI MERGEÄ)

- Gate 1: MUST ≥ 99 %
- Gate 1b: MUST Top-1 ≥ 80 %
- Gate 2: SHOULD ≥ 95 %
- Gate 3: **toimintakertomus ≥ 90 %**
- Gate 4: hard_negative_violations == 0
- Gate 5: latency < 150 ms

---

## VAIHE 4 – ITERAATIOMALLI

Kun jokin gate failaa:

1. Tunnista **failaavat ID:t** raportista
2. Tarkista:
   - väärä momentti?
   - liian geneerinen tagi?
   - puuttuva synonyymi?
3. Korjaa **data ensin**, ei querya
4. Rebuild → reindex → rerun eval

ÄLÄ:
- säädä min_scorea korjataksesi precisionia
- lisää LLM:iä retrieval-vaiheeseen

---

## VAIHE 5 – VALMIS-KRITEERI

Prosessi katsotaan valmiiksi, kun:
- kaikki laatuportit PASS
- precision@1 ≥ 80 %
- toimintakertomus ≥ 90 %
- hard negatives = 0

Tämän jälkeen indeksi on **tuotantokelpoinen kuntalaiskäyttöön** ja valmis yhdistettäväksi Lapua-tilinpäätös-RAGiin.

---

## LOPPUOHJE CURSORILLE

Tämä ei ole analyysitehtävä.
Tämä ei ole ehdotus.

➡️ **Toteuta vaiheet 1–5 järjestyksessä.**
➡️ **Älä muuta laatuportteja.**
➡️ **Raportoi vain faktatulokset.**