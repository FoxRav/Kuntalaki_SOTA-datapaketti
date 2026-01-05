# v10 – Epätoiminnallisuuden paljastava testipatteri (Adversarial Eval)

## Tavoite
v10:n tarkoitus on paljastaa **vektori-indeksin ja koko retrieval+graph+doc-mapping -putken epätoiminnallisuus** systemaattisesti.

v7.2/v8.1/v9 mittaavat “toimii kun kysytään oikein”.
v10 mittaa “toimiiko, kun kysymys on:
- epätäsmällinen
- harhaanjohtava
- monihyppyinen
- sisältää ristiriidan
- sekoittaa lait tai domainit
- vaatii taulukko-/liite-evidenssiä
- vaatii ajantasaisuuden (kynnysarvot) tai versioinnin”.

**Ei LoRAa.**

---

## 1) v10 Testauksen rakenne

### 1.1 Neljä testikoria
1) **Retrieval Robustness (LAW)**
2) **Graph Robustness (PATH/SUPPORT)**
3) **Document Evidence Robustness (DOC/EVIDENCE)**
4) **Safety/Uncertainty Robustness (ABSTAIN)**

### 1.2 Uudet mittarit (v10)
- **CONFUSION_FAIL**: väärä laki top-1, kun kysymys sisältää vahvan domain-ankkurin (esim. “kunnan”)
- **NEAR_MISS**: oikea osuma top-5 mutta ei top-1
- **HALLU_EVIDENCE**: viitataan dokumenttievidenssiin, jota ei löydy (sivu/taulukko/path puuttuu)
- **PATH_TRUNCATION**: normipolku puuttuu, vaikka viittausedge on olemassa
- **VERSION_DRIFT**: kynnysarvo/numero ei täsmää lain versioon (finlex_version)
- **ABSTAIN_RATE**: järjestelmä sanoo “en voi varmistaa” oikein (parempi kuin väärä varma vastaus)

Tavoitteet (alku):
- CONFUSION_FAIL ≤ 2%
- HALLU_EVIDENCE = 0
- VERSION_DRIFT = 0 (jos kysymys vaatii numeron)
- ABSTAIN oikein ≥ 90% niissä kysymyksissä, joissa data ei riitä

---

## 2) v10 Kysymysskeema (JSON)

Tee uusi eval-setti: `eval/v10/questions_adversarial.json`

Minimischema:
- `id`
- `category` (LAW/GRAPH/DOC/ABSTAIN)
- `query`
- `expected`:
  - `expected_law_any` (lista law_key)
  - `expected_nodes_any` (node_id list, optional)
  - `expected_doc_path_any` (page/section/table path, optional)
  - `required_anchor_terms` (2–5)
  - `must_abstain` (bool)
- `scoring`:
  - `pass_if_topk_contains` (k)
  - `pass_if_abstain` (bool)

---

## 3) 20 + 20 + 20 + 20 = 80 kysymyksen patteri (valmis pohja)

### 3.1 LAW: Confusion & Synonym attacks (20)
1. "kunnan laatimisvelvollisuus" (tahallinen lyhyys) – pitää ohjata KUNTA, ei KPL
2. "tilinpäätöksen laatiminen kirjanpitovelvollisella kunnalla" – sekoitus, priorisoi KUNTA + KPL top-2
3. "kuntakonsernin konsernitilinpäätös vai konsernitilinpäätös yhtiössä?" – pitää erottaa KUNTA vs OYL
4. "tilintarkastajan muistutus kunnan päätöksistä" – KUNTA/TILA sekaisin
5. "hankinnan kynnysarvot kunnassa" – HANK + mahdollinen KUNTA support
6. "liitetiedot kunnan taseessa" – KPL/KPA + KUNTA raja
7. "osakeyhtiön hallituksen vastuu kunnan tytäryhtiössä" – OYL primary, KUNTA support
8. "tasekirja ja toimintakertomus kunnassa" – KUNTA + KPL/KPA
9. "tuloslaskelmakaava kunnalla" – KUNTA/KPA
10. "poikkeus tilinpäätöksen määräajasta" – pitäisi löytää pykälä, ja jos ei ole: abstain
11. "kunnan alijäämäselvitys" – KUNTA
12. "tarkastuslautakunta tilinpäätös" – KUNTA
13. "tilintarkastuskertomus muistutus" – KUNTA/TILA disambiguointi
14. "rakennusurakka kynnysarvot" – HANK
15. "hankintasopimus vs puitejärjestely" – HANK
16. "konsernilainat ja eliminointi" – KUNTA/KPL (riippuen sanamuodosta)
17. "vastuusitoumukset liitetiedoissa" – KPL/KPA + KUNTA
18. "kunnan johdon vastuu vahingosta" – KUNTA/OYL (riippuen roolista)
19. "kunnan rahoituslaskelma" – KUNTA/KPA
20. "tilikausi kunnalla" – KUNTA

### 3.2 GRAPH: Multi-hop & Exception traps (20)
1. Kysymys, joka vaatii "poiketen"-ketjun (EXCEPTS)
2. Kysymys, joka vaatii määritelmän (DEFINES)
3. "sovelletaan mitä, jos…" (REFERS_TO ulkoiseen lakiin)
4. "jollei toisin säädetä" (pakota support)
5. "tämän lain 1 luvussa tarkoitetaan" (definition trigger)
6–20: rakenna 15 lisää valitsemalla solmuja, joilla on REFERS_TO/EXCEPTS/DEFINES edgejä (graph_debug --stats + sampling)

### 3.3 DOC: Evidence & Table attacks (20)
1. "missä tilinpäätöksen kohdassa näkyy kattamaton alijäämä" (page/section required)
2. "näytä taulukosta rahoituslaskelman nettoinvestoinnit" (table/cell)
3. "millä sivulla esitetään takaukset ja vastuusitoumukset" (liitetieto)
4. "löytyykö toimintakertomuksesta olennaiset tapahtumat" (para)
5–20: lisää 16 kysymystä, jotka kohdistuvat suoraan METRIC- ja TABLE-solmuihin (doc graph)

### 3.4 ABSTAIN: Unknown / out-of-scope / versioning (20)
1. "mikä on hankintalain EU-kynnysarvo tänään" (vaatii finlex_version; jos ei ajantasainen → abstain)
2. "mikä on Lapuan vuosikate 2024" (jos vain 2023 data → abstain)
3. "mikä on kunnan veroprosentti" (ei tässä corpus → abstain)
4. "anna juridinen neuvo henkilökohtaisessa riidassa" (abstain + ohjaus)
5–20: lisää 16 kysymystä, joiden tieto ei ole indeksissä tai vaatii ajanhetken

---

## 4) Eval-runner (v10)
Tee `scripts/run_v10_adversarial_eval.py`:
- aja pipeline normaalisti
- kerää:
  - top-5 law hits
  - graph path nodes/edges
  - doc evidence nodes
  - abstain-flag jos käytössä
- laske mittarit (CONFUSION_FAIL, NEAR_MISS, HALLU_EVIDENCE, VERSION_DRIFT, ABSTAIN)
- tallenna:
  - `reports/v10_adversarial_summary.md`
  - `reports/v10_adversarial_failures.md` (top-50 pahinta)

---

## 5) Tulosten perusteella tehtävä kehityssilmukka
1) Ota top-10 failure clusteria (termipohjainen ryhmittely)
2) Päätä korjaustyyppi:
- router rules
- pair guards
- anchor enrichment
- graph parsing
- doc mapping heuristics
- abstain policy
3) Tee yksi korjaus per commit + rerun v10

---

## 6) Seuraava askel (nyt)
1) Luo `eval/v10/questions_adversarial.json` (aloita 40 kysymyksellä: 10 per kategoria)
2) Toteuta runner ja raportointi
3) Aja baseline ja nosta 3 pahinta failure clusteria korjauslistaksi

