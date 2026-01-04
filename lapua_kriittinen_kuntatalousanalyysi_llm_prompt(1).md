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

