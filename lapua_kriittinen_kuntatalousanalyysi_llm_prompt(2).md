# Kuntalaki SOTA‑tason datapaketti – Cursor‑ohjeet

Tämä dokumentti antaa **täsmälliset, toteutettavat ohjeet Cursor AI:lle**, miten nykyinen Finlex / Akoma Ntoso ‑datapaketti muunnetaan **SOTA‑tasoiseksi AI‑analyysidataksi** (RAG, sääntöpohjainen analyysi, lakiviitteet, kunnalliset talousanalyysit).

---

## 0. Johtopäätös (status nyt)

Nykyinen rakenne:
```
finlex_statute_consolidated/
└── akn/fi/act/statute-consolidated/
    └── <VUOSI>/<LAKI>/<fin@>/main.xml
```

on **erinomainen primäärilähde** (Finlex XML, Akoma Ntoso 3.0), mutta:
- ❌ ei ole vielä analyysi‑ eikä RAG‑optimoitu
- ❌ ei ole helposti haettavissa pykälä-/momentti‑tasolla
- ❌ ei ole valmiiksi versioitu AI‑käyttöön

Tavoite: **yhden totuuden lähde → monikäyttöinen AI‑kerros**.

---

## 1. Kultainen lähde (DO NOT TOUCH)

### Säilytä muuttumattomana
```
finlex_statute_consolidated/akn/fi/act/statute-consolidated/
```

- Tämä on **kanoninen oikeudellinen lähde**
- Ei siivousta, ei muokkauksia
- Käytetään vain lukemiseen ja uudelleenrakentamiseen

---

## 2. Luo analyysikerros (UUSI rakenne)

Cursor: **luo uusi hakemisto** projektin juureen

```
analysis_layer/
├── metadata/
├── json/
├── markdown/
├── embeddings/
└── lineage/
```

---

## 3. XML → Normalisoitu JSON (ydinaskel)

### Cursor‑tehtävä
Kirjoita uusi skripti:
```
analysis_layer/build_kuntalaki_json.py
```

### Jokainen pykälä = yksi JSON‑objekti

**TARGET SCHEMA (pakollinen):**
```json
{
  "law": "Kuntalaki",
  "law_id": "410/2015",
  "finlex_version": "fin@20230780",
  "part": "VI",
  "chapter": "13",
  "chapter_title": "Kunnan talous",
  "section": "110",
  "section_title": "Talousarvio ja -suunnitelma",
  "moment": "1",
  "text": "Kunnan talousarvioon otetaan...",
  "effective_from": "2015-05-01",
  "in_force": true,
  "source": {
    "xml_path": "akn/fi/act/.../main.xml",
    "xpath": "/akomaNtoso/act/...",
    "finlex_url": "https://finlex.fi/..."
  }
}
```

### Säännöt
- § = oma tietue
- jokainen momentti = oma tietue
- **EI yhdistelyä**

---

## 4. Markdown‑kerros (LLM‑ystävällinen)

Luo:
```
analysis_layer/markdown/kuntalaki_410-2015.md
```

### Muoto
```md
## § 110 Talousarvio ja -suunnitelma

### 110.1 momentti
Kunnan talousarvioon otetaan...

_Lähde: Kuntalaki 410/2015, Finlex, voimassa_
```

Tämä kerros:
- ihmisluettava
- LLM‑ystävällinen
- helppo chunkata

---

## 5. Semanttiset tagit (SOTA‑ominaisuus)

Cursor: lisää JSON‑tuotantoon **automaattinen tagitus**:

```json
"tags": [
  "talousarvio",
  "alijäämä",
  "kuntakonserni",
  "investoinnit",
  "lainat",
  "arviointimenettely"
]
```

Tagit johdetaan:
- luvusta
- pykälän otsikosta
- avainsanoista

---

## 6. Versiointi ja aikajana (erittäin tärkeä)

Luo:
```
analysis_layer/lineage/kuntalaki_410-2015_versions.json
```

Sisältö:
```json
{
  "410/2015": [
    {
      "finlex": "fin@20150501",
      "effective_from": "2015-05-01"
    },
    {
      "finlex": "fin@20230780",
      "effective_from": "2023-01-05"
    }
  ]
}
```

Mahdollistaa kysymykset:
> "Mikä pykälä 110 tarkoitti vuonna 2018?"

---

## 7. Embedding‑kerros (RAG)

Kun JSON valmis:

- chunkkaa **momentti‑tasolla**
- 300–600 tokenia
- metadata mukaan (law_id, section, moment, finlex)

```
analysis_layer/embeddings/
└── kuntalaki_bge-m3.faiss
```

---

## 8. Käyttö AI‑analyyseissä

Tämän jälkeen AI pystyy:
- viittaamaan täsmällisesti (§, mom.)
- yhdistämään pykälät tilinpäätöksiin
- tunnistamaan **Kuntalain rikkomusriskit**
- vastaamaan: *"Rikkoako tämä talousarvio 110 §:ää?"*

---

## 9. Yhteenveto

| Kerros | Tila |
|------|------|
| Finlex XML | ✅ valmis |
| Normalisoitu JSON | ⛔ tee |
| Markdown | ⛔ tee |
| Tagitus | ⛔ tee |
| Embedding | ⛔ tee |

Tällä rakenteella Kuntalaki muuttuu:
**PDF‑laista → koneellisesti ymmärrettäväksi sääntökoneeksi**.


---

## 10. CURSOR AI – TÄSMÄLLISET TOIMINTAOHJEET (PAKOLLINEN)

Alla on **suora Cursor-prompt**, joka toteuttaa viimeiset SOTA-vaatimukset (110a-normalisointi, node_id, regressiotestit, talousfiltteri). **Kopioi tämä Cursor AI:lle ja suorita repojuuressa.**

---

### CURSOR PROMPT (EXECUTION MODE)

**Tehtävä:** Päivitä Kuntalaki-analyysikerros SOTA-tasolle alla olevien vaatimusten mukaisesti. Älä muuta Finlex XML -lähdettä.

#### A. Pykälätunnisteiden normalisointi
1. Päivitä `analysis_layer/build_kuntalaki_json.py`:
   - Lisää kentät:
     - `section_id` (string): esim. `110a`
     - `section_num` (int): esim. `110`
     - `section_suffix` (string|null): esim. `"a"`
   - Sääntö:
     - jos pykälän numero sisältää kirjaimen → jaa se num+suffix
     - `section_id = f"{section_num}{section_suffix or ''}"`

2. Varmista että **110 § ja 110 a § eivät koskaan yhdisty** missään vaiheessa.

---

#### B. Uniikki solmuavain (node_id)
1. Lisää jokaiseen JSON/JSONL-riviin:
```json
"law_key": "fi:act:410/2015",
"node_id": "410/2015:fin@20230780:110a:3"
```
2. Muodostus:
```
node_id = f"{law_id}:{finlex_version}:{section_id}:{moment}"
```
3. Lisää validointi: jos `node_id` duplikaatti → raise Exception.

---

#### C. Versioeheys (fin@-kontrolli)
1. Päivitä `analysis_layer/build_lineage.py`:
   - Lue fin@-versiot **hakemistorakenteesta**, ei kovakoodauksia
   - Tallenna:
```json
{
  "finlex": "fin@20230780",
  "effective_from": "YYYY-MM-DD",
  "source_xml": ".../main.xml"
}
```
2. Lisää tarkistus: JSONL:n `finlex_version` ∈ lineage → muuten FAIL.

---

#### D. Taloussuodatin (pre-filter RAG:lle)
1. Luo tiedosto:
```
analysis_layer/metadata/domain_filters.json
```
2. Sisältö:
```json
{
  "talous": {
    "required_tags": ["talous", "talousarvio", "alijäämä", "laina", "rahoitus"],
    "sections": ["110", "110a", "113", "114", "118", "129", "148"]
  }
}
```
3. Dokumentoi README: RAG-haku käyttää ensin domain-filteriä, sitten rerank.

---

#### E. Golden-set regressiotesti
1. Luo:
```
analysis_layer/tests/test_kuntalaki_semantic.py
```
2. Lisää vähintään 20 kysymystä, mm:
   - "kunnan talousarvion alijäämä ja kattaminen" → TOP-3 sisältää 110, 110a, 148
   - "erityisen vaikeassa taloudellisessa asemassa oleva kunta" → TOP-3 = 118
3. Testi FAIL jos odotettu pykälä puuttuu TOP-3:sta.

---

#### F. README-päivitys
Päivitä `analysis_layer/README.md`:
- kuvaa `section_id`, `node_id`
- kuvaa versioeheys
- kuvaa domain-filterit

---

### VALMIS-KRITEERI (ÄLÄ MERKITSE VALMIIKSI ENNEN NÄITÄ)
- [ ] 110 § ja 110 a § erillisinä kaikissa kerroksissa
- [ ] `node_id` uniikki ja validoitu
- [ ] fin@-versiot yhtenevät XML ↔ JSON ↔ lineage
- [ ] Golden-set testit vihreänä
- [ ] Talouskyselyt suodattuvat oikein

Kun nämä täyttyvät, Kuntalaki-analyysikerros täyttää **SOTA-vaatimukset** ja on valmis tuotantoon.
