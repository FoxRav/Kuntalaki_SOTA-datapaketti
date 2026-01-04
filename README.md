# Kuntalaki SOTA-datapaketti

Finlexin Kuntalaki (410/2015) Akoma Ntoso XML -muodosta **SOTA-tasoiseksi AI-analyysidataksi** muunnettuna.

## Rakenne

```
├── finlex_statute_consolidated/     # 🔒 Kultainen lähde (DO NOT TOUCH)
│   └── akn/fi/act/statute-consolidated/2015/410/
│       ├── fin@20230780/main.xml    # Ajantasaisin versio
│       └── fin@.../                 # Aiemmat versiot
│
├── analysis_layer/                  # ✅ AI-optimoitu analyysikerros
│   ├── json/                        # Normalisoitu JSON (pykälä/momentti-taso)
│   ├── markdown/                    # LLM-ystävällinen Markdown
│   ├── embeddings/                  # RAG-vektori-indeksit
│   ├── lineage/                     # Versiohistoria ja aikajana
│   └── metadata/                    # Lain metatiedot
│
├── akn_to_md.py                     # Perusmuunnostyökalu
├── akn_to_md_v2.py                  # Parannettu versio
└── md_clean.py                      # Markdown-siivous
```

## Tila

| Kerros | Tila | Tiedosto |
|--------|------|----------|
| Finlex XML | ✅ valmis | `finlex_statute_consolidated/` |
| Normalisoitu JSON | ✅ valmis | `analysis_layer/json/kuntalaki_410-2015.json` |
| JSONL (streaming) | ✅ valmis | `analysis_layer/json/kuntalaki_410-2015.jsonl` |
| Markdown | ✅ valmis | `analysis_layer/markdown/kuntalaki_410-2015.md` |
| Versiohistoria | ✅ valmis | `analysis_layer/lineage/kuntalaki_410-2015_versions.json` |
| Metadata | ✅ valmis | `analysis_layer/metadata/kuntalaki_410-2015_meta.json` |
| Embedding (RAG) | ✅ valmis | `analysis_layer/embeddings/chroma_db/` |

## JSON-skeema

Jokainen momentti on oma tietue:

```json
{
  "law": "Kuntalaki",
  "law_id": "410/2015",
  "finlex_version": "fin@20230780",
  "part": "VI OSA",
  "part_title": "TALOUS",
  "chapter": "13 luku",
  "chapter_title": "Kunnan talous",
  "section": "110",
  "section_title": "Talousarvio ja -suunnitelma",
  "moment": "1",
  "text": "Valtuuston on vuoden loppuun mennessä hyväksyttävä...",
  "effective_from": "2015-05-01",
  "in_force": true,
  "tags": ["talousarvio", "budjetti", "investoinnit"],
  "source": {
    "xml_path": "finlex_statute_consolidated/akn/.../main.xml",
    "finlex_url": "https://finlex.fi/fi/laki/ajantasa/2015/20150410",
    "xpath": "//subsection[@eId='...']"
  }
}
```

## Käyttö

### 1. JSON-datan uudelleengenerointi

```bash
python analysis_layer/build_kuntalaki_json.py
```

### 2. Markdown-version generointi

```bash
python analysis_layer/build_markdown.py
```

### 3. Versiohistorian päivitys

```bash
python analysis_layer/build_lineage.py
```

## Semanttiset tagit

Jokainen momentti sisältää automaattisesti johdetut tagit:

- **Luvun perusteella**: talous, hallinto, päätöksenteko
- **Avainsanojen perusteella**: alijäämä, arviointimenettely, tilintarkastus
- **Pykälän otsikon perusteella**: talousarvio ja -suunnitelma

## RAG-integraatio (ChromaDB)

Vektori-indeksi on valmiina käyttöön `analysis_layer/embeddings/chroma_db/`.

### Semanttinen haku

```python
from sentence_transformers import SentenceTransformer
from analysis_layer.vector_store.chroma_store import ChromaVectorStore

# Lataa malli ja yhdistä indeksiin
model = SentenceTransformer("BAAI/bge-m3")
store = ChromaVectorStore("analysis_layer/embeddings/chroma_db", "kuntalaki")

# Hae semanttisesti
query = "kunnan talousarvion alijäämä"
embedding = model.encode([query], normalize_embeddings=True)[0]
results = store.query(embedding.tolist(), n_results=5)

for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f"§ {meta['section']}.{meta['moment']} - {meta['section_title']}")
```

### Metadata-suodatus

```python
# Hae vain luvusta 13 (Kunnan talous)
results = store.query(embedding.tolist(), where={"chapter": "13 luku"})
```

### Indeksin uudelleenrakennus

```bash
python analysis_layer/build_embeddings.py
```

## AI-käyttötapaukset

Tämän datapaketin avulla AI pystyy:

1. **Viittaamaan täsmällisesti** (§ 110.2 mom.)
2. **Yhdistämään pykälät tilinpäätöksiin** (talousanalyysi)
3. **Tunnistamaan kuntalain rikkomusriskit**
4. **Vastaamaan**: *"Rikkooko tämä talousarvio 110 §:ää?"*
5. **Aikajanakyselyt**: *"Mikä pykälä 110 tarkoitti vuonna 2018?"*

## Tilastot

- **Momentteja**: 421
- **Pykäliä**: 150
- **Lukuja**: 21
- **Osia**: 8
- **Versioita**: 13

## Lähde

- **Data**: [Finlex avoin data](https://data.finlex.fi/)
- **Formaatti**: Akoma Ntoso 3.0
- **Lisenssi**: CC BY 4.0

## Riippuvuudet

```
lxml
chromadb
sentence-transformers
```

```bash
pip install lxml chromadb sentence-transformers
```

**Huom**: Windows-ympäristössä aseta ennen ajoa:
```powershell
$env:USE_TF="0"
$env:USE_TORCH="1"
```
