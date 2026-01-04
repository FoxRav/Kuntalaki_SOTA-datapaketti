# Embedding-kerros (RAG) - ChromaDB

Vektori-indeksi kuntalain semanttiseen hakuun.

## Tila

- **Indeksi**: `chroma_db/` (ChromaDB persistent store)
- **Dokumentteja**: 421 momenttia
- **Malli**: BAAI/bge-m3 (monikielinen)
- **Metriikka**: Kosini-samankaltaisuus

## Käyttö

### Haku Pythonilla

```python
import sys
sys.path.insert(0, ".")

from sentence_transformers import SentenceTransformer
from analysis_layer.vector_store.chroma_store import ChromaVectorStore

# Lataa malli ja yhdistä indeksiin
model = SentenceTransformer("BAAI/bge-m3")
store = ChromaVectorStore("analysis_layer/embeddings/chroma_db", "kuntalaki")

# Hae
query = "kunnan talousarvion alijäämä"
embedding = model.encode([query], normalize_embeddings=True)[0]
results = store.query(embedding.tolist(), n_results=5)

for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f"§ {meta['section']}.{meta['moment']} - {meta['section_title']}")
```

### Metadata-suodatus

ChromaDB tukee metadata-suodatusta:

```python
# Hae vain talouspykälistä (luku 13)
results = store.query(
    embedding.tolist(),
    n_results=5,
    where={"chapter": "13 luku"},
)

# Hae pykälästä 110-120
results = store.query(
    embedding.tolist(),
    n_results=5,
    where={"section": {"$gte": "110", "$lte": "120"}},
)
```

## Indeksin uudelleenrakennus

```bash
# Aseta ympäristömuuttujat (Windows)
$env:USE_TF="0"
$env:USE_TORCH="1"

# Aja
python analysis_layer/build_embeddings.py
```

## Testihaku

```bash
python analysis_layer/test_search.py
```

## Esimerkkituloksia

**Query**: "kunnan talousarvion alijäämä ja kattaminen"

| # | Pykälä | Otsikko | Score |
|---|--------|---------|-------|
| 1 | § 148.2 | Alijäämän kattamista koskevat siirtymäsäännökset | 0.680 |
| 2 | § 110.3 | Talousarvio ja -suunnitelma | 0.675 |
| 3 | § 110 a | Alijäämän kattamista koskevan määräajan jatkaminen | 0.654 |

**Query**: "erityisen vaikeassa taloudellisessa asemassa oleva kunta"

| # | Pykälä | Otsikko | Score |
|---|--------|---------|-------|
| 1 | § 118.1 | Erityisen vaikeassa taloudellisessa asemassa olevan kunnan arviointimenettely | 0.670 |
| 2 | § 118.5 | (sama) | 0.636 |
| 3 | § 118.7 | (sama) | 0.628 |

## Metadata-kentät

Jokainen dokumentti sisältää:

| Kenttä | Tyyppi | Esimerkki |
|--------|--------|-----------|
| `law` | string | "Kuntalaki" |
| `law_id` | string | "410/2015" |
| `section` | string | "110" |
| `moment` | string | "3" |
| `section_title` | string | "Talousarvio ja -suunnitelma" |
| `chapter` | string | "13 luku" |
| `chapter_title` | string | "Kunnan talous" |
| `tags` | JSON array | ["talousarvio", "budjetti"] |
| `in_force` | bool | true |

## Riippuvuudet

```
chromadb
sentence-transformers
```

## Skaalautuvuus

ChromaDB käsittelee ~100 000 dokumenttia paikallisesti. Jos tarvitaan enemmän, voidaan siirtyä Qdrantiin.
