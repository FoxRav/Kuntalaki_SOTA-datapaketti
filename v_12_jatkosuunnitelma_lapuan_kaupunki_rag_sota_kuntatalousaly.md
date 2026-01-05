# v12 – Jatkosuunnitelma (Lapuan kaupunki RAG)

## Päämäärä (lukitse tämä)
Rakennetaan **SOTA-tason kuntatalousäly**, joka:
- ymmärtää tilinpäätökset, talousarviot ja konsernirakenteet
- laskee tunnusluvut oikein ja näyttää laskentajäljen
- soveltaa kuntalakia ja kirjanpitosääntelyä tilanteeseen
- tunnistaa riskit, poikkeamat ja ristiriidat
- kieltäytyy oikein, jos evidenssi ei riitä

v12 keskittyy **laskennalliseen päättelyyn, ristiriitoihin ja todellisiin dokumentteihin**.

---

## Lähtötilanne
- v10.1: adversarial robustness (CONFUSION, HALLU, VERSION) ✅
- v11: table-aware finance retrieval + numeric accuracy ✅

v11 on lukittu baseline. v12 ei saa rikkoa v11-gateja.

---

## v12 ydinidea
**Ihmismäinen kuntatalousajattelu = numerot + normi + konteksti + epävarmuus**

v12 tuo kolme uutta kyvykkyyttä:
1) **Calc-trace reasoning** (laskentajälki pakollinen)
2) **Cross-document & cross-year reasoning** (vertailut, trendit)
3) **Ristiriitojen ja riskien tunnistus** ("punainen lippu" -ajattelu)

---

## v12 uudet komponentit

### A) Reasoning v12 – Calc Engine
- Toteuta eksplisiittinen **calc_trace**:
  - jokainen johdettu luku = kaava + lähdeluvut + sivu/taulukko/rivi
- Tunnusluvut (minimi):
  - vuosikate, toimintakate, tilikauden tulos
  - lainakanta / asukas
  - kassan riittävyys (pv)
  - suhteellinen velkaantuneisuus

### B) Data v12 – Multi-year & real-doc
- Lisää **useampi tilikausi** (esim. 2022–2024)
- Lisää **oikeita PDF-parsintoja** synteettisen rinnalle
- Versionoi data: `doc_version`, `year`, `source_type (synthetic|real)`

### C) Retrieval v12 – Cross-doc
- Kysymykset voivat vaatia:
  - usean taulukon yhdistämistä
  - kahden vuoden vertailua
- Retrieval palauttaa **evidence setin**, ei yhtä osumaa

### D) Risk & Contradiction Layer
- Säännöt (esimerkkejä):
  - vuosikate < poistot → rakenteellinen alijäämäriski
  - alijäämäinen tulos useana vuotena → Kuntalaki-häly
  - konserniyhtiö tappiollinen, kunta voitollinen → huomio omistajaohjauksesta
- Output: "Havainto" + "Miksi tämä on riski" + "Mihin sääntöön/lakiin liittyy"

---

## v12 eval-strategia

### Eval-setit
1. **FIN_CALC** – pakotettu laskenta (gate)
2. **FIN_TREND** – kahden vuoden vertailu (gate)
3. **FIN_RISK** – riskin tunnistus (gate)
4. **LAW_FIN_COMBO** – laki + numero + johtopäätös (gate)
5. **ABSTAIN_HARD** – puuttuva/rikki data (gate)

### Uudet gatet (ehdotus)
- CALC_TRACE_OK ≥ 95%
- NUMERIC_ACCURACY = 100%
- TREND_CORRECT ≥ 95%
- RISK_DETECTION_PRECISION ≥ 90%
- CITATION_COVERAGE ≥ 90%
- ABSTAIN_CORRECT = 100%

OVERALL = FAIL jos yksikin gate FAIL

---

## v12 työlista (järjestyksessä)
1) Suunnittele ja lukitse **calc_trace JSON -schema**
2) Implementoi calc-engine (ei LLM:lle vapaita laskuja)
3) Lisää 2. tilikausi dataan
4) Rakenna cross-year retrieval
5) Luo v12 question set (80–120 casea)
6) Aja v12 baseline ja priorisoi FAILit

---

## Definition of Done (v12)
- Jokainen johdettu luku sisältää laskentajäljen
- Riskivastaukset sisältävät perustellun hälytyksen
- Kaikki v12 gatet PASS
- v11 ei regressioidu

---

## Pysyvät periaatteet
- Ei arvailua, ei implisiittisiä laskuja
- Numerot tulevat taulukoista tai eivät ollenkaan
- Gate-FAIL = arkkitehtuurikorjaus, ei prompttihifistely
- Tämä ei ole chatbot, vaan **kuntatalouden analyysimoottori**

