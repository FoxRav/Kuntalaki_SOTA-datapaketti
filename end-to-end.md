# End-to-End: Miten vastaukset generoidaan

Tämä dokumentti kuvaa **koko prosessin** siitä, miten käyttäjän kysymyksestä päädytään lakitekstiin perustuvaan vastaukseen.

---

## 1. Yleiskuva (Pipeline)

```
┌─────────────────┐
│  Käyttäjän      │
│  kysymys        │
│  (suomeksi)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Law Router     │  ← Tunnistaa relevantin lain/lait
│  (keyword-based)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Embedding      │  ← Muuntaa kysymyksen vektoriksi
│  (BAAI/bge-m3)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Multi-Law      │  ← Hakee top-k osumaa jokaisesta
│  Query          │     valitusta laki-indeksistä
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Reranking      │  ← Router bonus, pair guards,
│  (deterministic)│     diversity rule
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vastaus        │  ← Top-1 osuman lakiteksti
│  (momentti)     │
└─────────────────┘
```

---

## 2. Vaihe 1: Law Router (Lain valinta)

### Sijainti
`shared/query_rules/law_router.py`

### Mitä tekee
Router analysoi kysymyksen avainsanat ja päättää, mihin lakeihin haku kohdistetaan.

### Triggerit (esimerkkejä)

| Avainsana | Laki | Weight |
|-----------|------|--------|
| `kunta`, `kunnan` | Kuntalaki | +1.0 |
| `tilinpäätös`, `tase` | Kirjanpitolaki | +0.5 |
| `tilintarkastaja` | Tilintarkastuslaki | +1.0 |
| `hankinta`, `kilpailutus` | Hankintalaki | +1.0 |
| `konserni`, `yhtiö` | Osakeyhtiölaki | +0.5 |
| `liitetiedot`, `kaava` | Kirjanpitoasetus | +0.5 |

### Tulos
```python
{
    "kuntalaki_410_2015": 0.45,
    "kirjanpitolaki_1336_1997": 0.25,
    "tilintarkastuslaki_1141_2015": 0.15,
    ...
}
```

Normalisoidut painot → top-2 lakia valitaan aina hakuun.

---

## 3. Vaihe 2: Embedding (Vektorointi)

### Malli
**BAAI/bge-m3** – monikielinen embedding-malli

### Sijainti
Käytetään `sentence-transformers` -kirjastolla:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-m3")
embedding = model.encode([query], normalize_embeddings=True)[0]
```

### Mitä tekee
Muuntaa tekstikysymyksen 1024-ulotteiseksi vektoriksi, joka kuvaa semanttista merkitystä.

---

## 4. Vaihe 3: ChromaDB-indeksit (Vektoritietokanta)

### Sijainti
Jokainen laki omassa indeksissään:
```
laws/kuntalaki_410_2015/analysis_layer/embeddings/chroma/
laws/kirjanpitolaki_1336_1997/analysis_layer/embeddings/chroma/
laws/tilintarkastuslaki_1141_2015/analysis_layer/embeddings/chroma/
laws/hankintalaki_1397_2016/analysis_layer/embeddings/chroma/
laws/osakeyhtiolaki_624_2006/analysis_layer/embeddings/chroma/
laws/kirjanpitoasetus_1339_1997/analysis_layer/embeddings/chroma/
```

### Indeksin sisältö (per momentti)
```json
{
    "node_id": "410/2015:fin@20230780:113:1",
    "law_key": "kuntalaki_410_2015",
    "section_num": 113,
    "section_id": "113",
    "moment": 1,
    "section_title": "Tilinpäätös",
    "text": "Kunnan tilinpäätökseen kuuluvat...",
    "anchors": ["tilinpäätös", "tuloslaskelma", "tase", "liitetiedot"]
}
```

### Haku
```python
results = collection.query(
    query_embeddings=[embedding],
    n_results=k,
    include=["documents", "metadatas", "distances"]
)
```

**Distance → Score**: `score = 1 - distance` (cosine similarity)

---

## 5. Vaihe 4: Multi-Law Query

### Sijainti
`scripts/run_cross_law_eval.py` → `multi_law_query()`

### Algoritmi
1. Router antaa painot per laki
2. Laske `k_per_law = ceil(k_total * weight)` (minimi 2 per laki)
3. Hae top-k jokaisesta valitusta laki-indeksistä
4. Yhdistä tulokset yhteen listaan

### Esimerkki
```
Query: "kunnan tilinpäätöksen laatimisvelvollisuus"

Router weights:
- kuntalaki: 0.55
- kirjanpitolaki: 0.25
- tilintarkastuslaki: 0.20

k_total = 10 → k_per_law:
- kuntalaki: 6
- kirjanpitolaki: 3
- tilintarkastuslaki: 2
```

---

## 6. Vaihe 5: Reranking (Deterministinen)

### Sijainti
`scripts/run_cross_law_eval.py` → `apply_reranking_rules()`

### Säännöt

#### 6.1 Router Bonus (+0.02)
```python
if hit["law_key"] == top1_law:
    hit["score"] += ROUTER_BONUS  # 0.02
```

#### 6.2 Pair Guards (Boosting/Penalizing)
```python
PAIR_GUARD_RULES = [
    # "kunnan" → boost Kuntalaki, penalize KPL
    {"query_terms": ["kunnan"], 
     "boost_law": "kuntalaki_410_2015", "boost_amount": 0.03,
     "penalize_law": "kirjanpitolaki_1336_1997", "penalty_amount": 0.03},
    
    # "konserni" → boost OYL
    {"query_terms": ["konserni"], 
     "boost_law": "osakeyhtiolaki_624_2006", "boost_amount": 0.02},
    
    # "tilintarkastaja" → boost Tilintarkastuslaki
    {"query_terms": ["tilintarkastaja"], 
     "boost_law": "tilintarkastuslaki_1141_2015", "boost_amount": 0.02},
    ...
]
```

#### 6.3 Diversity Rule (score-ero < 0.02)
```python
if abs(best_score_law1 - best_score_law2) < DIVERSITY_GAP:
    # Varmista, että top-k sisältää vähintään 1 hitti toiseksi parhaasta laista
```

### Lopputulos
Järjestetty lista top-k osumia, paras ensin.

---

## 7. Vaihe 6: Vastauksen muodostaminen

### Top-1 osuma
```json
{
    "law_key": "kuntalaki_410_2015",
    "section_num": 113,
    "moment": 1,
    "score": 0.72,
    "text": "Kunnan tilinpäätökseen kuuluvat tase, tuloslaskelma, rahoituslaskelma ja niiden liitteenä olevat tiedot sekä talousarvion toteutumisvertailu ja toimintakertomus."
}
```

### Vastausformaatti
```markdown
## Kysymys 1
**Kysymys:** Mitkä Kuntalain säännökset velvoittavat kunnan laatimaan tilinpäätöksen...

**Lähde:** Kuntalaki 410/2015 § 113, momentti 1

**Vastaus:**
Kunnan tilinpäätökseen kuuluvat tase, tuloslaskelma, rahoituslaskelma ja niiden 
liitteenä olevat tiedot sekä talousarvion toteutumisvertailu ja toimintakertomus.
```

---

## 8. Koko prosessi koodina

```python
# 1. Lataa indeksit
indices = load_all_law_indices()  # ChromaDB collections

# 2. Lataa embedding-malli
model = SentenceTransformer("BAAI/bge-m3")

# 3. Käyttäjän kysymys
query = "Mitkä Kuntalain säännökset velvoittavat kunnan laatimaan tilinpäätöksen?"

# 4. Router: valitse lait
weights = route_query(query, available_laws=list(indices.keys()))
# → {"kuntalaki_410_2015": 0.6, "kirjanpitolaki_1336_1997": 0.4}

# 5. Laske k per laki
k_per_law = calculate_k_per_law(weights, total_k=10, min_k=2)
# → {"kuntalaki_410_2015": 6, "kirjanpitolaki_1336_1997": 4}

# 6. Vektoroi kysymys
embedding = model.encode([query], normalize_embeddings=True)[0].tolist()

# 7. Hae jokaisesta indeksistä
all_results = []
for law_key, k in k_per_law.items():
    results = indices[law_key].query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )
    for doc, meta, dist in zip(...):
        score = 1 - dist
        if score >= MIN_SCORE:  # 0.50
            all_results.append({
                "law_key": law_key,
                "score": score,
                "section_num": meta["section_num"],
                "moment": meta["moment"],
                "text": doc,
                ...
            })

# 8. Rerank
final_results = apply_reranking_rules(
    query, all_results, weights,
    ROUTER_BONUS=0.02, DIVERSITY_GAP=0.02, PAIR_GUARD_RULES=...
)

# 9. Palauta top-1 vastaus
answer = final_results[0]
print(f"Lähde: {answer['law_key']} § {answer['section_num']}, mom {answer['moment']}")
print(f"Teksti: {answer['text']}")
```

---

## 9. Tiedostorakenne

```
Kuntalaki_SOTA-datapaketti/
├── laws/                          # Lakikohtaiset datat
│   ├── kuntalaki_410_2015/
│   │   └── analysis_layer/
│   │       ├── json/              # Normalisoitu JSON/JSONL
│   │       └── embeddings/chroma/ # Vektori-indeksi
│   ├── kirjanpitolaki_1336_1997/
│   ├── tilintarkastuslaki_1141_2015/
│   ├── hankintalaki_1397_2016/
│   ├── osakeyhtiolaki_624_2006/
│   └── kirjanpitoasetus_1339_1997/
├── shared/
│   ├── query_rules/
│   │   └── law_router.py          # Lain valintalogiikka
│   └── eval_harness/              # Testikysymykset
├── scripts/
│   ├── run_cross_law_eval.py      # Multi-law haku + eval
│   ├── run_sota_eval_20.py        # SOTA 20 kysymyksen eval
│   └── generate_sota_answers.py   # Vastausten generointi
└── reports/
    ├── sota_vastaukset_20.md      # Generoidut vastaukset
    └── sota_eval_20_report.md     # Eval-raportti
```

---

## 10. Laatuportit (Quality Gates)

| Portti | Kriteeri | Tila |
|--------|----------|------|
| STRICT | ≥ 95% oikea laki + pykälä + momentti | ✅ 100% |
| ROUTING | ≥ 95% oikea laki top-k:ssa | ✅ 100% |
| Hard Neg | = 0 vääriä lakeja top-1:ssä | ✅ 0 |
| Latency | < 150 ms | ✅ ~50 ms |
| SOTA 20 | ≥ 90% (18/20) oikea laki | ✅ 100% |

---

## 11. Yhteenveto

1. **Query → Router** – Päättää mihin lakeihin haetaan
2. **Query → Embedding** – Vektoroi kysymys
3. **Embedding → ChromaDB** – Hakee samankaltaiset momentit
4. **Merge + Rerank** – Yhdistää ja järjestää tulokset
5. **Top-1 → Vastaus** – Palauttaa parhaan osuman lakitekstin

Koko prosessi on **deterministinen** (ei LLM:ää retrievalissa) ja **testattavissa** (eval-skriptit + quality gates).

