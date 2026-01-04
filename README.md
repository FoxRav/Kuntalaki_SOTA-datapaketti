# Kuntalaki SOTA-datapaketti

Finlexin Kuntalaki (410/2015) Akoma Ntoso XML -muodosta **SOTA-tasoiseksi AI-analyysidataksi** muunnettuna.

## Tila

| Komponentti | Tila | Huomio |
|-------------|------|--------|
| JSON/JSONL (momenttitaso) | ✅ valmis | 421 momenttia, uniikki `node_id` |
| Markdown | ✅ valmis | LLM-ystävällinen |
| ChromaDB embedding | ✅ valmis | BAAI/bge-m3 |
| Anchors (v4) | ✅ valmis | Momenttispesifit avainsanat |
| Query boost/penalty | ✅ valmis | Pair-guards (110/110a, 113/114) |
| Eval v3 testit | ✅ **100% PASS** | MUST 100%, SHOULD 100%, k=10 |

## Repon rakenne

```
├── analysis_layer/              # AI-optimoitu analyysikerros
│   ├── json/                    # Normalisoitu JSON (momenttitaso)
│   ├── markdown/                # LLM-ystävällinen Markdown
│   ├── embeddings/              # ChromaDB-indeksi (EI repossa)
│   ├── lineage/                 # Versiohistoria
│   ├── metadata/                # Domain filters, metatiedot
│   ├── vector_store/            # ChromaDB wrapper
│   ├── query_boost.py           # Query-time boost/penalty
│   └── tests/                   # Golden-set testit
│
├── eval/                        # Retrieval-evaluaatio
│   ├── v3/                      # V3 testikehys (150 kysymystä)
│   └── questions_kuntalaki_golden.json
│
└── *.py                         # Muunnostyökalut
```

**HUOM**: Seuraavat EIVÄT ole repossa (vain paikallisesti):
- `finlex_statute_consolidated/` - Finlex XML raakadata
- `analysis_layer/embeddings/chroma_db/` - Vektori-indeksi (generoitava)

## Pikastartti

### 1. Kloonaa ja asenna

```bash
git clone https://github.com/FoxRav/Kuntalaki_SOTA-datapaketti.git
cd Kuntalaki_SOTA-datapaketti
pip install lxml chromadb sentence-transformers pytest
```

### 2. Hanki Finlex-data (tarvitaan vain jos haluat generoida itse)

```bash
# Lataa Finlex avoin data: https://data.finlex.fi/
# Pura: finlex_statute_consolidated/akn/fi/act/statute-consolidated/2015/410/
```

### 3. Generoi indeksi (tai käytä valmiita JSON-tiedostoja)

```bash
# Jos sinulla on Finlex-data:
python analysis_layer/build_kuntalaki_json.py
python analysis_layer/build_embeddings.py

# Testaa
pytest analysis_layer/tests/ -v
```

## JSON-skeema (v4)

Jokainen momentti on oma tietue:

```json
{
  "law": "Kuntalaki",
  "law_id": "410/2015",
  "law_key": "fi:act:410/2015",
  "node_id": "410/2015:fin@20230780:110a:3",
  "finlex_version": "fin@20230780",
  "part": "VI OSA",
  "chapter": "13 luku",
  "section_id": "110a",
  "section_num": 110,
  "section_suffix": "a",
  "section_title": "COVID-19-epidemiaan liittyvät poikkeukset",
  "moment": 3,
  "text": "...",
  "tags": ["talousarvio", "covid-19", "korona", "poikkeuslaki"],
  "anchors": ["covid", "korona", "epidemia", "poikkeuslaki"],
  "in_force": true,
  "source": { ... }
}
```

### V4 uudet kentät

| Kenttä | Tarkoitus |
|--------|-----------|
| `node_id` | Uniikki tunniste jokaiselle momentille |
| `section_id` | Pykälätunniste kirjainsuffiksilla (110, 110a, 62b) |
| `anchors` | Momenttispesifit avainsanat (query-time rerank) |

## RAG-käyttö

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

### Query boost (suositeltu)

```python
from analysis_layer.query_boost import apply_query_boost

# Hae ensin ChromaDB:stä
raw_results = store.query(embedding.tolist(), n_results=10)

# Paranna järjestystä boost-säännöillä
hits = [
    {"section_id": m["section_id"], "moment": m["moment"], 
     "score": 1 - d, "anchors": m.get("anchors", [])}
    for m, d in zip(raw_results["metadatas"][0], raw_results["distances"][0])
]
boosted = apply_query_boost(query, hits)
```

## Eval v3 tulokset

```
Configuration: k=10, min_score=0.50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL:     150/150 (100.0%) ✅
MUST:      50/50   (100.0%) ✅
SHOULD:    60/60   (100.0%) ✅
Top-1 hit: 91.3%
Precision@1: 88.0%
MRR: 0.944
Latency: ~45ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Aja testit itse

```bash
python eval/v3/run_kuntalaki_eval_v3.py --k 10 --min-score 0.50
```

## Tilastot

- **Momentteja**: 421
- **Pykäliä**: 150
- **Lukuja**: 21
- **Osia**: 8
- **Finlex-versioita**: 13

## Lisenssi & lähde

- **Data**: [Finlex avoin data](https://data.finlex.fi/) (CC BY 4.0)
- **Formaatti**: Akoma Ntoso 3.0
- **Koodi**: MIT

## Riippuvuudet

```
lxml
chromadb>=0.4.0
sentence-transformers
pytest
```

```bash
pip install lxml chromadb sentence-transformers pytest
```

**Windows**: Aseta ennen ajoa:
```powershell
$env:USE_TF="0"
$env:USE_TORCH="1"
```
