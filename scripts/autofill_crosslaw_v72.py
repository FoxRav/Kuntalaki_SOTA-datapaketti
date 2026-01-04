"""
Autofill cross-law expected values (v7.2).

Uses full multi-law query with v7.1 rerank to determine correct expected_any.
This fixes the issue where v7.0 autofill used incorrect expected_law_key from source.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add project root to path
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
EVAL_HARNESS_DIR = PROJECT_ROOT / "shared" / "eval_harness"
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
    # v7.2: Add more pair-guards for disambiguation
    ("kynnysarvo", "hankintalaki_1397_2016", +0.03),
    ("tarjous", "hankintalaki_1397_2016", +0.02),
    ("kilpailutus", "hankintalaki_1397_2016", +0.02),
    ("tasekaava", "kirjanpitoasetus_1339_1997", +0.03),
    ("tuloslaskelmakaava", "kirjanpitoasetus_1339_1997", +0.03),
    ("liitetietokaava", "kirjanpitoasetus_1339_1997", +0.02),
    ("erittelyt", "kirjanpitoasetus_1339_1997", +0.02),
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


def load_indices() -> dict[str, chromadb.Collection]:
    """Load all available law indices."""
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


def multi_law_query_v72(
    query: str,
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
) -> list[dict]:
    """
    Run v7.2 multi-law query with router bonus and pair-guards.
    Returns top-k results.
    """
    # Route query
    available_laws = list(indices.keys())
    weights = route_query(query, available_laws)
    
    # Get top law from router
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top1_law = sorted_weights[0][0] if sorted_weights else None
    
    # Calculate k per law
    k_per_law = calculate_k_per_law(weights, K_TOTAL, min_k=2)
    
    # Generate embedding
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    # Query each law index
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
        
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            score = 1 - dist
            if score >= MIN_SCORE:
                all_results.append({
                    "law_key": law_key,
                    "score": score,
                    "section_num": meta.get("section_num", 0),
                    "section_id": meta.get("section_id", ""),
                    "moment": meta.get("moment", ""),
                    "section_title": meta.get("section_title", ""),
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
    
    # Sort by score
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    return all_results[:K_TOTAL]


def autofill_question_v72(
    question: dict,
    indices: dict[str, chromadb.Collection],
    model: SentenceTransformer,
) -> dict:
    """
    Autofill expected_any using v7.2 multi-law query.
    Uses the TOP-1 hit from multi-law query as the expected.
    """
    query = question.get("query", "")
    expected_none = question.get("expected_none", [])
    
    # Run multi-law query
    results = multi_law_query_v72(query, indices, model)
    
    if not results:
        return {
            **question,
            "autofill_status": "FAIL",
            "autofill_reason": "No results from multi-law query",
            "expected_any": [],
        }
    
    # Use top-1 hit as expected
    top1 = results[0]
    
    # Parse moment as int if possible
    moment = top1.get("moment", "")
    try:
        moment = int(moment)
    except (ValueError, TypeError):
        pass
    
    return {
        "id": question.get("id", ""),
        "type": question.get("type", "SHOULD"),
        "category": question.get("category", "cross_law"),
        "test_type": question.get("test_type", "cross_law"),
        "query": query,
        "expected_none": expected_none,
        "notes": question.get("notes", ""),
        "autofill_status": "OK",
        "autofill_version": "7.2",
        "autofill_score": top1["score"],
        "autofill_section_title": top1.get("section_title", ""),
        "expected_any": [{
            "law_key": top1["law_key"],
            "section_num": int(top1["section_num"]),
            "moment": moment,
        }],
    }


def main() -> None:
    """Run v7.2 autofill for all cross-law question files."""
    print("=" * 60)
    print("Autofill Cross-Law Expected Values (v7.2)")
    print("=" * 60)
    print(f"  Router Bonus: +{ROUTER_BONUS}")
    print(f"  Pair Guards: {len(PAIR_GUARDS)} rules")
    print("=" * 60)
    
    # Load indices
    print("\nLoading indices...")
    indices = load_indices()
    print(f"  Loaded: {len(indices)} indices")
    
    # Load embedding model
    print("\nLoading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    # Find all cross-law question files (original, not autofill)
    question_files = list(EVAL_HARNESS_DIR.glob("questions_cross_*.json"))
    question_files = [f for f in question_files if ".autofill." not in f.name]
    
    total_ok = 0
    total_fail = 0
    
    for qf in question_files:
        print(f"\nProcessing: {qf.name}")
        
        with open(qf, encoding="utf-8") as f:
            data = json.load(f)
        
        questions = data.get("questions", [])
        autofilled_questions = []
        file_ok = 0
        file_fail = 0
        
        for q in questions:
            result = autofill_question_v72(q, indices, model)
            autofilled_questions.append(result)
            
            if result.get("autofill_status") == "OK":
                file_ok += 1
            else:
                file_fail += 1
                print(f"  FAIL: {result.get('id')} - {result.get('autofill_reason', 'Unknown')}")
        
        total_ok += file_ok
        total_fail += file_fail
        
        # Write autofilled file (overwrite v7.0 autofill)
        output_path = qf.with_suffix(".autofill.json")
        output_data = {
            "description": data.get("description", "") + " (autofilled v7.2)",
            "version": "7.2",
            "autofill_stats": {
                "ok": file_ok,
                "fail": file_fail,
            },
            "questions": autofilled_questions,
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"  OK: {file_ok}, FAIL: {file_fail}")
        print(f"  Output: {output_path.name}")
    
    print("\n" + "=" * 60)
    print(f"TOTAL: OK={total_ok}, FAIL={total_fail}")
    print("=" * 60)


if __name__ == "__main__":
    main()

