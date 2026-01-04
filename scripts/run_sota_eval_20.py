"""
SOTA Evaluation - 20 Expert Questions on Finnish Municipal Finance Law.

Tests the system's ability to:
1. Identify correct law → section → moment
2. Connect answers to correct financial statement parts
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

# Law index configurations
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

# 20 SOTA Expert Questions
SOTA_QUESTIONS = [
    # A. Kunnan tilinpäätös ja Kuntalaki
    {
        "id": "SOTA-A01",
        "category": "A. Kunnan tilinpäätös",
        "query": "Mitkä Kuntalain säännökset velvoittavat kunnan laatimaan tilinpäätöksen ja missä määräajassa se on tehtävä?",
        "expected_laws": ["kuntalaki_410_2015"],
        "expected_topics": ["tilinpäätös", "määräaika", "laatiminen"],
    },
    {
        "id": "SOTA-A02",
        "category": "A. Kunnan tilinpäätös",
        "query": "Millä edellytyksillä kunta on velvollinen laatimaan konsernitilinpäätöksen ja mitkä yhteisöt siihen sisällytetään?",
        "expected_laws": ["kuntalaki_410_2015"],
        "expected_topics": ["konsernitilinpäätös", "konserni", "tytäryhteisö"],
    },
    {
        "id": "SOTA-A03",
        "category": "A. Kunnan tilinpäätös",
        "query": "Miten alijäämän kattamisvelvollisuus vaikuttaa kunnan toimintakertomuksen sisältöön?",
        "expected_laws": ["kuntalaki_410_2015"],
        "expected_topics": ["alijäämä", "kattaminen", "toimintakertomus"],
    },
    {
        "id": "SOTA-A04",
        "category": "A. Kunnan tilinpäätös",
        "query": "Mitkä taloudelliset tiedot on pakollista esittää kunnan toimintakertomuksessa?",
        "expected_laws": ["kuntalaki_410_2015"],
        "expected_topics": ["toimintakertomus", "taloudelliset tiedot"],
    },
    # B. Kirjanpitolaki vs. Kuntalaki
    {
        "id": "SOTA-B05",
        "category": "B. Kirjanpitolaki vs. Kuntalaki",
        "query": "Missä tilanteissa Kirjanpitolakia sovelletaan kuntaan ja milloin Kuntalaki syrjäyttää sen?",
        "expected_laws": ["kuntalaki_410_2015", "kirjanpitolaki_1336_1997"],
        "expected_topics": ["soveltaminen", "syrjäyttäminen"],
    },
    {
        "id": "SOTA-B06",
        "category": "B. Kirjanpitolaki vs. Kuntalaki",
        "query": "Miten kunnan tuloslaskelman ja taseen kaavat eroavat yleisen kirjanpitovelvollisen kaavoista?",
        "expected_laws": ["kirjanpitoasetus_1339_1997", "kuntalaki_410_2015"],
        "expected_topics": ["tuloslaskelma", "tase", "kaava"],
    },
    {
        "id": "SOTA-B07",
        "category": "B. Kirjanpitolaki vs. Kuntalaki",
        "query": "Voiko kunta poiketa kirjanpitolain arvostusperiaatteista ja millä perusteilla?",
        "expected_laws": ["kirjanpitolaki_1336_1997", "kuntalaki_410_2015"],
        "expected_topics": ["arvostus", "poikkeaminen"],
    },
    # C. Kuntakonserni ja tytäryhtiöt
    {
        "id": "SOTA-C08",
        "category": "C. Kuntakonserni",
        "query": "Miten määräysvalta määritellään kuntakonsernissa ja miten se vaikuttaa konsernitilinpäätökseen?",
        "expected_laws": ["kuntalaki_410_2015"],
        "expected_topics": ["määräysvalta", "konserni", "konsernitilinpäätös"],
    },
    {
        "id": "SOTA-C09",
        "category": "C. Kuntakonserni",
        "query": "Millaiset sisäiset liiketapahtumat on eliminoitava kuntakonsernin tilinpäätöksessä?",
        "expected_laws": ["kuntalaki_410_2015", "kirjanpitolaki_1336_1997"],
        "expected_topics": ["eliminointi", "sisäiset", "konserni"],
    },
    {
        "id": "SOTA-C10",
        "category": "C. Kuntakonserni",
        "query": "Miten kunnan antamat takaukset ja vastuusitoumukset esitetään tilinpäätöksen liitetiedoissa?",
        "expected_laws": ["kuntalaki_410_2015", "kirjanpitolaki_1336_1997"],
        "expected_topics": ["takaus", "vastuusitoumus", "liitetiedot"],
    },
    # D. Hankinnat ja sopimusvastuut
    {
        "id": "SOTA-D11",
        "category": "D. Hankinnat",
        "query": "Millä tavoin hankintalain kynnysarvot vaikuttavat kunnan sopimusvastuiden raportointiin?",
        "expected_laws": ["hankintalaki_1397_2016"],
        "expected_topics": ["kynnysarvo", "sopimus", "raportointi"],
    },
    {
        "id": "SOTA-D12",
        "category": "D. Hankinnat",
        "query": "Miten puitejärjestely eroaa hankintasopimuksesta ja miten ero näkyy taloudellisissa sitoumuksissa?",
        "expected_laws": ["hankintalaki_1397_2016"],
        "expected_topics": ["puitejärjestely", "hankintasopimus"],
    },
    # E. Tilintarkastus ja valvonta
    {
        "id": "SOTA-E13",
        "category": "E. Tilintarkastus",
        "query": "Missä tilanteissa tilintarkastaja voi antaa huomautuksen kunnan tilinpäätöksestä?",
        "expected_laws": ["tilintarkastuslaki_1141_2015", "kuntalaki_410_2015"],
        "expected_topics": ["huomautus", "tilintarkastaja"],
    },
    {
        "id": "SOTA-E14",
        "category": "E. Tilintarkastus",
        "query": "Miten tilintarkastuskertomuksen havainnot vaikuttavat vastuuvapauden myöntämiseen?",
        "expected_laws": ["kuntalaki_410_2015", "tilintarkastuslaki_1141_2015"],
        "expected_topics": ["vastuuvapaus", "tilintarkastuskertomus"],
    },
    # F. Rahoitus ja vastuut
    {
        "id": "SOTA-F15",
        "category": "F. Rahoitus",
        "query": "Miten rahoituslaskelman tiedot tukevat arviota kunnan maksuvalmiudesta?",
        "expected_laws": ["kuntalaki_410_2015", "kirjanpitoasetus_1339_1997"],
        "expected_topics": ["rahoituslaskelma", "maksuvalmius"],
    },
    {
        "id": "SOTA-F16",
        "category": "F. Rahoitus",
        "query": "Millä edellytyksillä kunnan johdon vahingonkorvausvastuu voi syntyä taloudellisista päätöksistä?",
        "expected_laws": ["kuntalaki_410_2015"],
        "expected_topics": ["vahingonkorvaus", "vastuu", "johto"],
    },
    # G. Erityistilanteet
    {
        "id": "SOTA-G17",
        "category": "G. Erityistilanteet",
        "query": "Miten poikkeukselliset taloudelliset tapahtumat tulee käsitellä kunnan tilinpäätöksessä?",
        "expected_laws": ["kuntalaki_410_2015", "kirjanpitolaki_1336_1997"],
        "expected_topics": ["poikkeuksellinen", "tilinpäätös"],
    },
    {
        "id": "SOTA-G18",
        "category": "G. Erityistilanteet",
        "query": "Voiko kunta poiketa tilinpäätöksen esittämistavasta ja millä oikeudellisilla perusteilla?",
        "expected_laws": ["kuntalaki_410_2015", "kirjanpitolaki_1336_1997"],
        "expected_topics": ["esittämistapa", "poikkeaminen"],
    },
    {
        "id": "SOTA-G19",
        "category": "G. Erityistilanteet",
        "query": "Miten julkisuusperiaate vaikuttaa tilinpäätösasiakirjojen tietosisältöön ja salassapitoon?",
        "expected_laws": ["kuntalaki_410_2015"],
        "expected_topics": ["julkisuus", "salassapito"],
    },
    {
        "id": "SOTA-G20",
        "category": "G. Erityistilanteet",
        "query": "Miten ristiriita Kuntalain ja muun erityislainsäädännön välillä ratkaistaan talousraportoinnissa?",
        "expected_laws": ["kuntalaki_410_2015"],
        "expected_topics": ["ristiriita", "erityislainsäädäntö"],
    },
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
            except Exception as e:
                print(f"  Warning: Could not load {law_key}: {e}")
    return indices


def multi_law_query(
    query: str,
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
) -> list[dict]:
    """Run multi-law query with v7.2 rerank."""
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
                    "section_num": meta.get("section_num", 0),
                    "section_title": meta.get("section_title", ""),
                    "moment": meta.get("moment", ""),
                    "chapter": meta.get("chapter", ""),
                    "chapter_title": meta.get("chapter_title", ""),
                    "text": doc[:300] + "..." if len(doc) > 300 else doc,
                    "node_id": meta.get("node_id", ""),
                })
    
    # Apply router bonus
    if top1_law:
        for r in all_results:
            if r["law_key"] == top1_law:
                r["score"] += ROUTER_BONUS
    
    # Apply pair-guards
    query_lower = query.lower()
    for term, law_key, adjustment in PAIR_GUARDS:
        if term in query_lower:
            for r in all_results:
                if r["law_key"] == law_key:
                    r["score"] += adjustment
    
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:K_TOTAL]


def evaluate_question(question: dict, results: list[dict]) -> dict:
    """Evaluate a single SOTA question."""
    expected_laws = question.get("expected_laws", [])
    
    # Check if any expected law is in top-3
    top3_laws = [r["law_key"] for r in results[:3]]
    found_expected = any(law in top3_laws for law in expected_laws)
    
    # Check if top-1 is an expected law
    top1_correct = results[0]["law_key"] in expected_laws if results else False
    
    return {
        "found_expected_in_top3": found_expected,
        "top1_correct": top1_correct,
        "top3_laws": top3_laws,
    }


def format_law_name(law_key: str) -> str:
    """Format law key to readable name."""
    names = {
        "kuntalaki_410_2015": "Kuntalaki",
        "kirjanpitolaki_1336_1997": "Kirjanpitolaki",
        "kirjanpitoasetus_1339_1997": "Kirjanpitoasetus",
        "tilintarkastuslaki_1141_2015": "Tilintarkastuslaki",
        "hankintalaki_1397_2016": "Hankintalaki",
        "osakeyhtiolaki_624_2006": "Osakeyhtiölaki",
    }
    return names.get(law_key, law_key)


def main() -> None:
    """Run SOTA evaluation with 20 expert questions."""
    print("=" * 70)
    print("SOTA-ARVIOINTI: Talous & Suomen laki (20 kysymystä)")
    print("=" * 70)
    
    # Load indices
    print("\nLoading indices...")
    indices = load_indices()
    print(f"  Loaded: {len(indices)} indices")
    
    # Load model
    print("\nLoading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    # Run evaluation
    print("\n" + "=" * 70)
    print("RUNNING EVALUATION")
    print("=" * 70)
    
    results_all: list[dict] = []
    correct_count = 0
    total_latency = 0.0
    
    for i, q in enumerate(SOTA_QUESTIONS):
        start = time.perf_counter()
        results = multi_law_query(q["query"], indices, model)
        latency = (time.perf_counter() - start) * 1000
        total_latency += latency
        
        eval_result = evaluate_question(q, results)
        
        if eval_result["found_expected_in_top3"]:
            correct_count += 1
            status = "OK"
        else:
            status = "FAIL"
        
        print(f"\n[{i+1}/20] {q['id']} ({q['category']})")
        print(f"  Q: {q['query'][:70]}...")
        print(f"  Expected: {', '.join([format_law_name(l) for l in q['expected_laws']])}")
        
        if results:
            top1 = results[0]
            print(f"  Top-1: {format_law_name(top1['law_key'])} §{top1['section_id']}.{top1['moment']} - {top1['section_title']}")
            print(f"  Score: {top1['score']:.4f} | Latency: {latency:.0f}ms")
        else:
            print(f"  Top-1: No results")
        
        print(f"  Status: [{status}]")
        
        results_all.append({
            "id": q["id"],
            "category": q["category"],
            "query": q["query"],
            "expected_laws": q["expected_laws"],
            "found_expected": eval_result["found_expected_in_top3"],
            "top1_correct": eval_result["top1_correct"],
            "top_results": results[:5],
            "latency_ms": latency,
        })
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    avg_latency = total_latency / len(SOTA_QUESTIONS)
    pass_rate = correct_count / len(SOTA_QUESTIONS) * 100
    
    print(f"\nCorrect (expected law in top-3): {correct_count}/20 ({pass_rate:.0f}%)")
    print(f"Average latency: {avg_latency:.1f}ms")
    
    # Per category
    categories = {}
    for r in results_all:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "correct": 0}
        categories[cat]["total"] += 1
        if r["found_expected"]:
            categories[cat]["correct"] += 1
    
    print("\nPer Category:")
    for cat, stats in sorted(categories.items()):
        pct = stats["correct"] / stats["total"] * 100
        print(f"  {cat}: {stats['correct']}/{stats['total']} ({pct:.0f}%)")
    
    # SOTA verdict
    print("\n" + "=" * 70)
    if correct_count >= 18:
        print("VERDICT: SOTA-TASO SAAVUTETTU (18-20 oikeaa)")
    elif correct_count >= 15:
        print("VERDICT: HYVÄ TASO (15-17 oikeaa)")
    elif correct_count >= 12:
        print("VERDICT: KOHTALAINEN TASO (12-14 oikeaa)")
    else:
        print("VERDICT: KEHITETTÄVÄÄ (< 12 oikeaa)")
    print("=" * 70)
    
    # Save results
    output_path = PROJECT_ROOT / "reports" / "sota_eval_20_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "correct": correct_count,
                "total": 20,
                "pass_rate": pass_rate,
                "avg_latency_ms": avg_latency,
            },
            "categories": categories,
            "questions": results_all,
        }, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")
    
    # Generate markdown report
    report_path = PROJECT_ROOT / "reports" / "sota_eval_20_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# SOTA-arviointi: Talous & Suomen laki (20 kysymystä)\n\n")
        f.write(f"**Päivämäärä:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"## Yhteenveto\n\n")
        f.write(f"- **Oikein:** {correct_count}/20 ({pass_rate:.0f}%)\n")
        f.write(f"- **Keskimääräinen latenssi:** {avg_latency:.1f}ms\n\n")
        
        if correct_count >= 18:
            f.write("**VERDICT: SOTA-TASO SAAVUTETTU**\n\n")
        elif correct_count >= 15:
            f.write("**VERDICT: HYVÄ TASO**\n\n")
        else:
            f.write("**VERDICT: KEHITETTÄVÄÄ**\n\n")
        
        f.write("## Tulokset per kategoria\n\n")
        f.write("| Kategoria | Oikein | Yhteensä | % |\n")
        f.write("|-----------|--------|----------|---|\n")
        for cat, stats in sorted(categories.items()):
            pct = stats["correct"] / stats["total"] * 100
            f.write(f"| {cat} | {stats['correct']} | {stats['total']} | {pct:.0f}% |\n")
        
        f.write("\n## Yksityiskohtaiset tulokset\n\n")
        for r in results_all:
            status = "OK" if r["found_expected"] else "FAIL"
            f.write(f"### {r['id']} [{status}]\n\n")
            f.write(f"**Kysymys:** {r['query']}\n\n")
            f.write(f"**Odotettu laki:** {', '.join([format_law_name(l) for l in r['expected_laws']])}\n\n")
            
            if r["top_results"]:
                f.write("**Top-3 tulokset:**\n\n")
                for j, hit in enumerate(r["top_results"][:3], 1):
                    f.write(f"{j}. **{format_law_name(hit['law_key'])}** §{hit['section_id']}.{hit['moment']} - {hit['section_title']} (score: {hit['score']:.4f})\n")
            f.write("\n")
    
    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()

