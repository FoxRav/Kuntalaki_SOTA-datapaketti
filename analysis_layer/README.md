# Kuntalaki Analysis Layer - SOTA v4

Finlexin Kuntalaki (410/2015) muunnettuna **SOTA-tasoiseksi AI-analyysidataksi**.

## Tila

| Kerros | Tila | Huomio |
|--------|------|--------|
| Finlex XML | 🔒 paikallinen | Ei repossa |
| Normalisoitu JSON | ✅ valmis | 421 momenttia |
| Markdown | ✅ valmis | LLM-ystävällinen |
| Tagitus | ✅ valmis | Automaattinen + manuaalinen |
| Anchors (v4) | ✅ valmis | Momenttispesifit avainsanat |
| ChromaDB embedding | 🔧 generoitava | Ei repossa |
| Golden-set testit | ✅ 27/27 passed | |
| Eval v3 | ✅ 100% PASS | 150 kysymystä |

## V4 parannukset

### 1. Anchors (momenttispesifit avainsanat)

Jokainen momentti sisältää `anchors[]`-kentän:

```json
{
  "section_id": "115",
  "moment": 1,
  "anchors": ["tavoitteiden toteutuminen", "olennaiset tapahtumat", 
              "sisäinen valvonta", "riskienhallinta"]
}
```

Anchors mahdollistaa tarkan momenttitason erottelun haussa.

### 2. Query boost & pair-guards

`query_boost.py` sisältää:

- **Boost-säännöt**: "covid" → boost 110a, "konserni" → boost 114
- **Penalty-säännöt**: "ei konserni" → penalty 114
- **Anchor-overlap rerank**: Query-termi + anchor = score boost

### 3. Section ID normalisointi

```json
{
  "section_id": "110a",
  "section_num": 110,
  "section_suffix": "a"
}
```

§110 ja §110a ovat aina erillisiä tietueita kaikissa kerroksissa.

### 4. Uniikki node_id

```
410/2015:fin@20230780:110a:3
```

Muoto: `{law_id}:{finlex_version}:{section_id}:{moment}`

## Kansiorakenne

```
analysis_layer/
├── json/
│   ├── kuntalaki_410-2015.json      # Koko laki yhtenä JSON-tiedostona
│   └── kuntalaki_410-2015.jsonl     # Yksi momentti per rivi (streaming)
├── markdown/
│   └── kuntalaki_410-2015.md
├── embeddings/
│   ├── chroma_db/                   # (generoitava, ei repossa)
│   └── README.md
├── lineage/
│   └── kuntalaki_410-2015_versions.json
├── metadata/
│   ├── kuntalaki_410-2015_meta.json
│   └── domain_filters.json
├── tests/
│   ├── test_kuntalaki_semantic.py
│   └── test_anchors.py
├── vector_store/
│   ├── __init__.py
│   └── chroma_store.py
├── query_boost.py                   # V4: boost/penalty-säännöt
├── build_kuntalaki_json.py
├── build_markdown.py
├── build_lineage.py
├── build_embeddings.py
├── validate_kuntalaki_layer.py
└── README.md
```

## Käyttö

### 1. Generoi JSON (vaatii Finlex XML:n)

```bash
python analysis_layer/build_kuntalaki_json.py
```

### 2. Generoi ChromaDB-indeksi

```bash
python analysis_layer/build_embeddings.py
```

### 3. Aja validointi

```bash
python analysis_layer/validate_kuntalaki_layer.py
```

### 4. Aja testit

```bash
pytest analysis_layer/tests/ -v
```

## Haku ChromaDB:stä

### Perus semanttinen haku

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

### Query boost (suositeltu tuotannossa)

```python
from analysis_layer.query_boost import apply_query_boost

# Hae ensin raakadata
raw_results = store.query(embedding.tolist(), n_results=10)

# Muunna hit-listaksi
hits = []
for meta, dist in zip(raw_results["metadatas"][0], raw_results["distances"][0]):
    hits.append({
        "section_id": meta["section_id"],
        "moment": meta["moment"],
        "score": 1 - dist,
        "anchors": meta.get("anchors", []),
        "node_id": meta["node_id"],
    })

# Paranna järjestystä boost-säännöillä
boosted = apply_query_boost(query, hits)
```

### Metadata-suodatus

```python
# Hae vain talouspykälistä
results = store.query(
    embedding.tolist(),
    n_results=5,
    where={"section_num": {"$gte": 110, "$lte": 120}},
)

# Hae vain voimassa olevat
results = store.query(
    embedding.tolist(),
    n_results=5,
    where={"in_force": True},
)
```

## Domain Filters

`metadata/domain_filters.json` sisältää valmiit suodattimet:

```json
{
  "talous": {
    "required_tags": ["talous", "talousarvio", "alijäämä", "laina"],
    "sections": ["110", "110a", "113", "114", "118", "129", "148"]
  }
}
```

## Valmis-kriteerit (v4)

- [x] § 110 ja § 110a erillisinä kaikissa kerroksissa
- [x] `node_id` uniikki ja validoitu
- [x] `anchors[]` momenttispesifit avainsanat
- [x] Query boost pair-guards (110/110a, 113/114)
- [x] fin@-versiot yhtenevät XML ↔ JSON ↔ lineage
- [x] Golden-set testit vihreänä
- [x] Eval v3: 100% PASS (150 kysymystä)

## Riippuvuudet

```
lxml
chromadb>=0.4.0
sentence-transformers
pytest
```
