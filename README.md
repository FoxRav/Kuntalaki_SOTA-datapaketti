# Kunnallinen Talous Law Stack (v5)

**Suomen kunnallisen talous- ja valvontadomainin lainsäädäntö SOTA-tasoisena AI-analyysidatana.**

Finlexin Akoma Ntoso XML -muodosta muunnettuna momenttitason JSON/JSONL-dataksi, vektori-indeksillä (ChromaDB/bge-m3) ja deterministisellä query-time reitityksellä.

## Lait

| Laki | Säädös | Momentteja | Tila |
|------|--------|-----------|------|
| **Kuntalaki** | 410/2015 | 421 | ✅ Indeksoitu |
| **Kirjanpitolaki** | 1336/1997 | 385 | ✅ Indeksoitu |
| **Tilintarkastuslaki** | 1141/2015 | 357 | ✅ Indeksoitu |
| **Hankintalaki** | 1397/2016 | 454 | ✅ Indeksoitu |
| **Osakeyhtiölaki** | 624/2006 | 919 | ✅ Indeksoitu |
| **Yhteensä** | - | **2536** | ✅ |

## Arkkitehtuuri

```
├── analysis_layer/           # Kuntalaki (legacy, toimii)
│   ├── json/                 # Normalisoitu JSON/JSONL
│   ├── embeddings/           # ChromaDB (EI repossa)
│   ├── query_boost.py        # Query-time boost/penalty
│   └── tests/                # Golden-set testit
│
├── laws/                     # Multi-laki rakenne (v5)
│   ├── kirjanpitolaki_1336_1997/
│   ├── tilintarkastuslaki_1141_2015/
│   ├── hankintalaki_1397_2016/
│   └── osakeyhtiolaki_624_2006/
│
├── shared/                   # Jaettu infrastruktuuri
│   ├── law_catalog.json      # Lakikatalogi
│   ├── cross_refs.json       # Ristiinviittaukset
│   ├── schemas/              # Yhteinen datamoodi
│   ├── query_rules/          # Law router
│   │   └── law_router.py     # Deterministinen reititys
│   └── utils/                # Geneerinen law builder
│
├── scripts/                  # Ajoskriptit
│   ├── build_all_embeddings.py
│   └── multi_law_query.py    # Multi-laki haku
│
└── eval/                     # Evaluaatio
    └── v3/                   # 150 kysymyksen testipatteri
```

## Pikastartti

### 1. Kloonaa ja asenna

```bash
git clone https://github.com/FoxRav/Kuntalaki_SOTA-datapaketti.git
cd Kuntalaki_SOTA-datapaketti
pip install lxml chromadb sentence-transformers pytest
```

### 2. Hanki Finlex-data

```bash
# Lataa: https://data.finlex.fi/
# Pura: finlex_statute_consolidated/
```

### 3. Generoi indeksit

```bash
# Kuntalaki
python analysis_layer/build_kuntalaki_json.py
python analysis_layer/build_embeddings.py

# Kaikki muut lait kerralla
python scripts/build_all_embeddings.py
```

### 4. Testaa multi-laki haku

```bash
python scripts/multi_law_query.py
```

## Multi-laki reititys

```python
from shared.query_rules.law_router import route_query

# Deterministinen reititys avainsanojen perusteella
query = "tilinpäätöksen liitetiedot ja tase"
routes = route_query(query)
# {'kirjanpitolaki_1336_1997': 1.0}

query = "julkisen hankinnan kynnysarvo"
routes = route_query(query)
# {'hankintalaki_1397_2016': 1.0}

query = "osakeyhtiön hallituksen vastuu"
routes = route_query(query)
# {'osakeyhtiolaki_624_2006': 1.0}
```

## Testikyselyjen tulokset

```
Query: kunnan talousarvion alijäämä → Kuntalaki §110, §148, §110a ✅
Query: tilinpäätöksen liitetiedot → Kirjanpitolaki §1, §6, §13 ✅
Query: tilintarkastajan huomautus → Tilintarkastuslaki §1, §5 ✅
Query: julkisen hankinnan kynnysarvo → Hankintalaki §25, §26 ✅
Query: osakeyhtiön hallituksen vastuu → Osakeyhtiölaki §9, §16a ✅
```

## JSON-skeema (v5)

```json
{
  "law": "Kirjanpitolaki",
  "law_id": "1336/1997",
  "law_key": "fi:act:1336/1997",
  "node_id": "1336/1997:fin@20251006:3:1:1",
  "finlex_version": "fin@20251006",
  "chapter": "3 luku",
  "chapter_title": "Tilinpäätös",
  "section_id": "1",
  "section_title": "Tilinpäätöksen sisältö",
  "moment": "1",
  "text": "...",
  "tags": ["tilinpäätös", "tase", "tuloslaskelma"],
  "anchors": ["tilinpäätös", "tase", "tuloslaskelma", "liitetiedot"],
  "in_force": true
}
```

## Eval tulokset (Kuntalaki v4)

```
Configuration: k=10, min_score=0.50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL:     150/150 (100.0%) ✅
MUST:      50/50   (100.0%) ✅
SHOULD:    60/60   (100.0%) ✅
Top-1:     91.3%
Precision@1: 88.0%
MRR: 0.944
Latency: ~45ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Tilastot (v5)

| Laki | Momentteja | Kuvaus |
|------|-----------|--------|
| Kuntalaki | 421 | Kuntahallinon perusta |
| Kirjanpitolaki | 385 | Kirjanpitovelvollisuus |
| Tilintarkastuslaki | 357 | Tilintarkastus |
| Hankintalaki | 454 | Julkiset hankinnat |
| Osakeyhtiölaki | 919 | Yhtiöoikeus |
| **Yhteensä** | **2536** | 5 lakia |

## Roadmap

1. ✅ **v4**: Kuntalaki SOTA (100% pass)
2. ✅ **v5**: Multi-laki rakenne + kaikki 5 lakia
3. 🔜 **v5.1**: Kirjanpitoasetus (1339/1997)
4. 📋 **v6**: Cross-law eval ja multi-law reranking

## Lisenssi & lähde

- **Data**: [Finlex avoin data](https://data.finlex.fi/) (CC BY 4.0)
- **Koodi**: MIT

## Riippuvuudet

```bash
pip install lxml chromadb sentence-transformers pytest
```

**Windows**: Aseta ennen ajoa:
```powershell
$env:USE_TF="0"
$env:USE_TORCH="1"
```
