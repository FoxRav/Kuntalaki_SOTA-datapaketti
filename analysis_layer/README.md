# Kuntalaki Analysis Layer - SOTA

Finlexin Kuntalaki (410/2015) muunnettuna **SOTA-tasoiseksi AI-analyysidataksi**.

## Tila

| Kerros | Tila |
|--------|------|
| Finlex XML | ✅ valmis |
| Normalisoitu JSON | ✅ valmis |
| Markdown | ✅ valmis |
| Tagitus | ✅ valmis |
| Embedding (ChromaDB) | ✅ valmis |
| Golden-set testit | ✅ 27/27 passed |

## SOTA-kentät

### Pykälätunnisteet

```json
{
  "section_id": "110a",
  "section_num": 110,
  "section_suffix": "a"
}
```

- `section_id`: Täydellinen pykälätunniste (esim. "110a", "62b")
- `section_num`: Numeerinen osa (esim. 110)
- `section_suffix`: Kirjainosa tai null (esim. "a", null)

**Tärkeää**: § 110 ja § 110a ovat aina erillisiä tietueita.

### Uniikki solmuavain (node_id)

```json
{
  "law_key": "fi:act:410/2015",
  "node_id": "410/2015:fin@20230780:110a:3"
}
```

- `law_key`: Kanoninen avain laille
- `node_id`: Uniikki tunniste jokaiselle momentille
  - Muoto: `{law_id}:{finlex_version}:{section_id}:{moment}`
  - Duplikaatit aiheuttavat virheen rakennusvaiheessa

## Versioeheys

`lineage/kuntalaki_410-2015_versions.json` sisältää:

```json
{
  "finlex": "fin@20230780",
  "effective_from": "2015-05-01",
  "source_xml": "finlex_statute_consolidated/akn/.../main.xml"
}
```

Validointi: JSONL:n `finlex_version` täytyy löytyä lineagesta.

## Taloussuodatin (Domain Filters)

`metadata/domain_filters.json` määrittelee RAG-hakujen esisuodattimet:

```json
{
  "talous": {
    "required_tags": ["talous", "talousarvio", "alijäämä", "laina", "rahoitus"],
    "sections": ["110", "110a", "113", "114", "118", "129", "148"]
  }
}
```

Käyttö RAG-haussa:
1. Suodata ensin domain-filtterillä
2. Sitten semanttinen haku
3. Lopuksi rerank

## Golden-set testit

`tests/test_kuntalaki_semantic.py` sisältää 25+ testikysymystä:

```bash
pytest analysis_layer/tests/test_kuntalaki_semantic.py -v
```

Testit varmistavat:
- Oikeat pykälät löytyvät TOP-3:sta
- § 110 ja § 110a ovat erillisiä
- Indeksissä on vähintään 400 dokumenttia

## Käyttö

### Haku ChromaDB:stä

```python
from sentence_transformers import SentenceTransformer
from analysis_layer.vector_store.chroma_store import ChromaVectorStore

model = SentenceTransformer("BAAI/bge-m3")
store = ChromaVectorStore("analysis_layer/embeddings/chroma_db", "kuntalaki")

query = "kunnan talousarvion alijäämä"
embedding = model.encode([query], normalize_embeddings=True)[0]
results = store.query(embedding.tolist(), n_results=5)

for meta in results["metadatas"][0]:
    print(f"§ {meta['section_id']}.{meta['moment']} - {meta['section_title']}")
```

### Metadata-suodatus

```python
# Hae vain talouspykälistä (section_num 110-120)
results = store.query(
    embedding.tolist(),
    n_results=5,
    where={"section_num": {"$gte": 110, "$lte": 120}},
)
```

### Uudelleenrakennus

```bash
# JSON
python analysis_layer/build_kuntalaki_json.py

# Lineage
python analysis_layer/build_lineage.py

# Embeddings
python analysis_layer/build_embeddings.py

# Testit
pytest analysis_layer/tests/test_kuntalaki_semantic.py -v
```

## Kansiorakenne

```
analysis_layer/
├── json/
│   ├── kuntalaki_410-2015.json
│   └── kuntalaki_410-2015.jsonl
├── markdown/
│   └── kuntalaki_410-2015.md
├── embeddings/
│   ├── chroma_db/
│   └── README.md
├── lineage/
│   └── kuntalaki_410-2015_versions.json
├── metadata/
│   ├── kuntalaki_410-2015_meta.json
│   └── domain_filters.json
├── tests/
│   └── test_kuntalaki_semantic.py
├── vector_store/
│   ├── __init__.py
│   └── chroma_store.py
├── build_kuntalaki_json.py
├── build_markdown.py
├── build_lineage.py
├── build_embeddings.py
└── README.md
```

## Riippuvuudet

```
lxml
chromadb
sentence-transformers
pytest
```

## Valmis-kriteerit

- [x] § 110 ja § 110a erillisinä kaikissa kerroksissa
- [x] `node_id` uniikki ja validoitu
- [x] fin@-versiot yhtenevät XML ↔ JSON ↔ lineage
- [x] Golden-set testit vihreänä
- [x] Talouskyselyt suodattuvat oikein

