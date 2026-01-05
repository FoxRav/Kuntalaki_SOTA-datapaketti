# v11 – Kehityssuunnitelma (Lapuan kaupunki RAG)

## Päämäärä (pidä tämä näkyvillä)
Rakennetaan järjestelmä, joka **ajattelee kuin ihminen kuntatalouden ja tilinpäätösten kontekstissa**:
- ymmärtää kuntien tilinpäätösasiakirjoja, toimintakertomuksia ja talousarvioita
- osaa tehdä perusteltuja johtopäätöksiä **kuntalain ja muun relevantin sääntelyn** näkökulmasta
- käyttää lähdeviitteitä ja kertoo epävarmuuden rehellisesti
- toimii tuotantotasolla: luotettava haku, selitys, toistettavat evalit ja jatkuva parantaminen

---

## Lähtötilanne (v10.1 lukittuna)
- v10.1 adversarial eval: **single-source-of-truth**, gate-logiikka tiukennettu, CONFUSION_FAIL korjattu retrievalissa.
- v10.1 on baseline: **älä riko sitä**. Kaikki uudet muutokset kulkevat v11-evalin kautta.

---

## v11 tavoite
**Siirrytään “lakikohdistuksesta” (cross-law confusion) kohti “kuntatalous-ajattelua”**:
1) talous- ja tilinpäätösdomainin ymmärrys (termistö, rakenteet, taulukot)
2) laskennallinen päättely (tunnusluvut, trendit, riskit)
3) normatiivinen päättely (kuntalaki: alijäämä, raportointivelvoitteet, konserniohjaus)
4) todennettavuus (viitteet, sivunumerot, taulukko-rivit, laskentajälki)

---

## v11 komponentit (deliverables)

### A) Data + rakenne
- **Doc parsing v11**: taulukot talteen (ei pelkkä teksti)
  - jokaiselle dokumentille: `doc_id`, `page`, `section`, `table_id`, `row/col`, `cell_text`, `normalized_value`
- **Unified schema**: talousrivit ja tunnusluvut normalisoidaan
  - Esim. tuloslaskelma, tase, rahoituslaskelma, liitetiedot, konserni

### B) Retrieval v11 (hybridi + ankkurit)
- Hybridi: BM25 + vektori + rakenne-ankkurit
- “Finance anchors”: termit ja rakenteet ("toimintakate", "vuosikate", "tilikauden tulos", "poistot", "lainakanta", "kassan riittävyys")
- “Table-aware retrieval”: kysymyksissä, joissa odotetaan lukua, ensisijainen osuma taulukon soluihin/riveihin

### C) Reasoning v11 (ihmismäinen analyysiputki)
- **3-vaiheinen vastausrunko** (sisäinen):
  1. Haku ja evidenssin valinta (sivu + taulukko + rivit)
  2. Laskenta / päättely (näytä laskentajälki)
  3. Johtopäätös + varoitukset + lain/ohjeen linkitys
- “Abstain oikein”: jos ei löydy evidenssiä tai data ristiriitainen → kieltäydy ja kerro miksi

### D) Eval v11 (uudet testit)
- Uusi eval-kokoelma: `eval/v11/questions_finance_adversarial.json`
  - Kategoriat: TABLE_NUMERIC, TREND, RISK, LAW_FINANCE, CONSOLIDATION, ABSTAIN
- **Uudet gatet (ehdotus)**
  - TABLE_EVIDENCE_RATE: % vastauksista joissa numero on sidottu taulukko-evidenssiin (gate)
  - CALC_TRACE_OK: laskentajälki täsmää (gate)
  - NUMERIC_DRIFT: sama kysymys eri ajossa ei saa muuttaa lukua ilman syytä (gate)
  - CITATION_COVERAGE: sivu/taulukko-rivi viitteet mukana (gate)
  - CONFUSION_FAIL_RATE pidetään edelleen (gate)

### E) Raportointi v11
- Sama periaate kuin v10.1: **single-source-of-truth JSON**
  - `reports/v11_*` generoituvat rendererillä

---

## v11 työlista (järjestyksessä)
1) **Määrittele v11 metrics contract** (case-tason säännöt + gate-kynnykset)
2) **Rakenna v11 question set** (min 60–100 casea)
   - 30% taulukko-lukukysymyksiä (pakottaa table-aware retrieval)
   - 30% trendi/vertailu (2 vuotta)
   - 20% lakikytkentä (kuntalaki + konserni)
   - 20% abstain (puuttuva tieto)
3) **Implementoi table-aware data layer** (solut + normalisointi)
4) **Implementoi table-first retrieval** numerokysymyksille
5) **Aja v11 eval** ja tee “top failures” -priorisointi

---

## v11 definition of done
- Kaikki v11 gatet PASS
- Numerokysymysten vastaukset sisältävät:
  - sivuviite + taulukko-id + rivin nimi + arvo
  - laskentajälki, jos johdettu tunnusluku
- Abstain toimii oikein (ei arvailla)
- v10.1 ei regressioidu

---

## Pysyvät periaatteet
- Ei keksitä lukuja tai pykäliä.
- Kaikki raportit ja päätelmät johdetaan evidenssistä.
- Gate-FAIL = korjaus retrieval/parse/reasoning, ei metriikkavääntö.

