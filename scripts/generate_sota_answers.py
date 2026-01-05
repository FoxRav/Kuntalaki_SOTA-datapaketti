"""
Generate SOTA answers report with full text.

Shows each question with the retrieved legal text as the answer.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

from shared.query_rules.law_router import route_query, calculate_k_per_law


# Configuration
K_TOTAL = 10
MIN_SCORE = 0.50
ROUTER_BONUS = 0.02
PAIR_GUARDS: list[tuple[str, str, float]] = [
    ("kunnan", "kuntalaki_410_2015", +0.03),
    ("kunnan", "kirjanpitolaki_1336_1997", -0.03),
    ("kunta", "kuntalaki_410_2015", +0.02),
    ("kunta", "kirjanpitolaki_1336_1997", -0.02),
    ("konserni", "osakeyhtiolaki_624_2006", +0.02),
    ("tilintarkastaja", "tilintarkastuslaki_1141_2015", +0.02),
    ("hankinta", "hankintalaki_1397_2016", +0.02),
    ("kynnysarvo", "hankintalaki_1397_2016", +0.03),
    ("tarjous", "hankintalaki_1397_2016", +0.02),
    ("kilpailutus", "hankintalaki_1397_2016", +0.02),
    ("tasekaava", "kirjanpitoasetus_1339_1997", +0.03),
    ("tuloslaskelmakaava", "kirjanpitoasetus_1339_1997", +0.03),
]

LAW_INDICES = {
    "kuntalaki_410_2015": {
        "chroma_path": PROJECT_ROOT / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kuntalaki",
    },
    "kirjanpitolaki_1336_1997": {
        "chroma_path": PROJECT_ROOT / "laws" / "kirjanpitolaki_1336_1997" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kirjanpitolaki",
    },
    "kirjanpitoasetus_1339_1997": {
        "chroma_path": PROJECT_ROOT / "laws" / "kirjanpitoasetus_1339_1997" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "kirjanpitoasetus",
    },
    "tilintarkastuslaki_1141_2015": {
        "chroma_path": PROJECT_ROOT / "laws" / "tilintarkastuslaki_1141_2015" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "tilintarkastuslaki",
    },
    "hankintalaki_1397_2016": {
        "chroma_path": PROJECT_ROOT / "laws" / "hankintalaki_1397_2016" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "hankintalaki",
    },
    "osakeyhtiolaki_624_2006": {
        "chroma_path": PROJECT_ROOT / "laws" / "osakeyhtiolaki_624_2006" / "analysis_layer" / "embeddings" / "chroma_db",
        "collection_name": "osakeyhtiolaki",
    },
}

SOTA_QUESTIONS = [
    {"id": "A01", "query": "Mitkä Kuntalain säännökset velvoittavat kunnan laatimaan tilinpäätöksen ja missä määräajassa se on tehtävä?"},
    {"id": "A02", "query": "Millä edellytyksillä kunta on velvollinen laatimaan konsernitilinpäätöksen ja mitkä yhteisöt siihen sisällytetään?"},
    {"id": "A03", "query": "Miten alijäämän kattamisvelvollisuus vaikuttaa kunnan toimintakertomuksen sisältöön?"},
    {"id": "A04", "query": "Mitkä taloudelliset tiedot on pakollista esittää kunnan toimintakertomuksessa?"},
    {"id": "B05", "query": "Missä tilanteissa Kirjanpitolakia sovelletaan kuntaan ja milloin Kuntalaki syrjäyttää sen?"},
    {"id": "B06", "query": "Miten kunnan tuloslaskelman ja taseen kaavat eroavat yleisen kirjanpitovelvollisen kaavoista?"},
    {"id": "B07", "query": "Voiko kunta poiketa kirjanpitolain arvostusperiaatteista ja millä perusteilla?"},
    {"id": "C08", "query": "Miten määräysvalta määritellään kuntakonsernissa ja miten se vaikuttaa konsernitilinpäätökseen?"},
    {"id": "C09", "query": "Millaiset sisäiset liiketapahtumat on eliminoitava kuntakonsernin tilinpäätöksessä?"},
    {"id": "C10", "query": "Miten kunnan antamat takaukset ja vastuusitoumukset esitetään tilinpäätöksen liitetiedoissa?"},
    {"id": "D11", "query": "Millä tavoin hankintalain kynnysarvot vaikuttavat kunnan sopimusvastuiden raportointiin?"},
    {"id": "D12", "query": "Miten puitejärjestely eroaa hankintasopimuksesta ja miten ero näkyy taloudellisissa sitoumuksissa?"},
    {"id": "E13", "query": "Missä tilanteissa tilintarkastaja voi antaa huomautuksen kunnan tilinpäätöksestä?"},
    {"id": "E14", "query": "Miten tilintarkastuskertomuksen havainnot vaikuttavat vastuuvapauden myöntämiseen?"},
    {"id": "F15", "query": "Miten rahoituslaskelman tiedot tukevat arviota kunnan maksuvalmiudesta?"},
    {"id": "F16", "query": "Millä edellytyksillä kunnan johdon vahingonkorvausvastuu voi syntyä taloudellisista päätöksistä?"},
    {"id": "G17", "query": "Miten poikkeukselliset taloudelliset tapahtumat tulee käsitellä kunnan tilinpäätöksessä?"},
    {"id": "G18", "query": "Voiko kunta poiketa tilinpäätöksen esittämistavasta ja millä oikeudellisilla perusteilla?"},
    {"id": "G19", "query": "Miten julkisuusperiaate vaikuttaa tilinpäätösasiakirjojen tietosisältöön ja salassapitoon?"},
    {"id": "G20", "query": "Miten ristiriita Kuntalain ja muun erityislainsäädännön välillä ratkaistaan talousraportoinnissa?"},
]


def load_indices() -> dict[str, chromadb.Collection]:
    """Load all law indices."""
    indices: dict[str, chromadb.Collection] = {}
    for law_key, config in LAW_INDICES.items():
        chroma_path = config["chroma_path"]
        if chroma_path.exists():
            try:
                client = chromadb.PersistentClient(path=str(chroma_path))
                collection = client.get_collection(config["collection_name"])
                indices[law_key] = collection
            except Exception:
                pass
    return indices


def multi_law_query(
    query: str,
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
) -> list[dict]:
    """Run multi-law query with full text."""
    available_laws = list(indices.keys())
    weights = route_query(query, available_laws)
    
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top1_law = sorted_weights[0][0] if sorted_weights else None
    
    k_per_law = calculate_k_per_law(weights, K_TOTAL, min_k=2)
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    all_results: list[dict] = []
    
    for law_key, k in k_per_law.items():
        if law_key not in indices:
            continue
        collection = indices[law_key]
        results = collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1 - dist
            if score >= MIN_SCORE:
                all_results.append({
                    "law_key": law_key,
                    "law_name": meta.get("law", ""),
                    "score": score,
                    "section_id": meta.get("section_id", ""),
                    "section_title": meta.get("section_title", ""),
                    "moment": meta.get("moment", ""),
                    "chapter_title": meta.get("chapter_title", ""),
                    "text": doc,  # Full text!
                })
    
    # Apply reranking
    if top1_law:
        for r in all_results:
            if r["law_key"] == top1_law:
                r["score"] += ROUTER_BONUS
    
    query_lower = query.lower()
    for term, law_key, adjustment in PAIR_GUARDS:
        if term in query_lower:
            for r in all_results:
                if r["law_key"] == law_key:
                    r["score"] += adjustment
    
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:5]


def format_law_name(law_key: str) -> str:
    """Format law key to readable name."""
    names = {
        "kuntalaki_410_2015": "Kuntalaki (410/2015)",
        "kirjanpitolaki_1336_1997": "Kirjanpitolaki (1336/1997)",
        "kirjanpitoasetus_1339_1997": "Kirjanpitoasetus (1339/1997)",
        "tilintarkastuslaki_1141_2015": "Tilintarkastuslaki (1141/2015)",
        "hankintalaki_1397_2016": "Hankintalaki (1397/2016)",
        "osakeyhtiolaki_624_2006": "Osakeyhtiölaki (624/2006)",
    }
    return names.get(law_key, law_key)


def main() -> None:
    """Generate SOTA answers report."""
    print("Loading indices...")
    indices = load_indices()
    print(f"  Loaded: {len(indices)} indices")
    
    print("Loading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    # Generate answers
    answers: list[dict] = []
    
    print("\nGenerating answers for 20 questions...\n")
    
    for q in SOTA_QUESTIONS:
        results = multi_law_query(q["query"], indices, model)
        answers.append({
            "id": q["id"],
            "query": q["query"],
            "results": results,
        })
        print(f"  [{q['id']}] Done")
    
    # Generate markdown report
    report_path = PROJECT_ROOT / "reports" / "sota_vastaukset_20.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# SOTA-arviointi: Vastaukset 20 kysymykseen\n\n")
        f.write(f"**Päivämäärä:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("---\n\n")
        
        for ans in answers:
            f.write(f"## {ans['id']}. {ans['query']}\n\n")
            
            if ans["results"]:
                top = ans["results"][0]
                f.write(f"**Lähde:** {format_law_name(top['law_key'])} §{top['section_id']}.{top['moment']} - {top['section_title']}\n\n")
                f.write(f"**Luku:** {top['chapter_title']}\n\n")
                f.write("**Vastaus lakitekstistä:**\n\n")
                f.write(f"> {top['text']}\n\n")
                
                # Additional relevant sections
                if len(ans["results"]) > 1:
                    f.write("**Muut relevantit pykälät:**\n\n")
                    for r in ans["results"][1:3]:
                        f.write(f"- {format_law_name(r['law_key'])} §{r['section_id']}.{r['moment']} - {r['section_title']}\n")
                    f.write("\n")
            else:
                f.write("*Ei tuloksia*\n\n")
            
            f.write("---\n\n")
    
    print(f"\nReport saved to: {report_path}")
    
    # Also print to console
    print("\n" + "=" * 70)
    print("VASTAUKSET")
    print("=" * 70)
    
    for ans in answers:
        print(f"\n## {ans['id']}. {ans['query']}\n")
        
        if ans["results"]:
            top = ans["results"][0]
            print(f"LÄHDE: {format_law_name(top['law_key'])} §{top['section_id']}.{top['moment']}")
            print(f"PYKÄLÄ: {top['section_title']}")
            print(f"\nVASTAUS:\n{top['text']}\n")
        
        print("-" * 70)


if __name__ == "__main__":
    main()

