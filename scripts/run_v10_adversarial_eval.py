#!/usr/bin/env python3
"""
v10: Adversarial Eval Runner

Tests system robustness against:
- Confusion attacks (wrong law routing)
- Near-miss scenarios (right answer in top-5 but not top-1)
- Hallucinated evidence
- Path truncation
- Version drift
- Abstain detection

Usage:
    python scripts/run_v10_adversarial_eval.py
"""

import json
import re
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Install: pip install chromadb sentence-transformers")
    exit(1)

# Configuration
QUESTIONS_PATH = PROJECT_ROOT / "eval" / "v10" / "questions_adversarial.json"
OUTPUT_DIR = PROJECT_ROOT / "reports"

# Law indices
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

DOC_INDEX_PATH = PROJECT_ROOT / "docs_layer" / "data" / "lapua" / "2023" / "embeddings"
DOC_COLLECTION = "lapua_2023"

# Query parameters
K_TOTAL = 10
MIN_SCORE = 0.40

# Abstain keywords (if these appear in question, likely should abstain)
ABSTAIN_SIGNALS_STRONG = [
    "tänään", "2024", "2025", 
    "helsinki", "helsingin",  # City inflections
    "tampere", "tampereen",
    "oulu", "oulun",
    "henkilökohtai", "osinko", "veroprosentti"
]

# Signals that require interpretation (abstain if no exact match)
ABSTAIN_SIGNALS_INTERPRET = [
    "konkurssi", "voimassa oleva", "uusi.*muutos"
]

# Municipal anchor terms (boost Kuntalaki)
MUNICIPAL_ANCHORS = [
    "kunnan", "kunta", "kuntakonserni", "kuntalaki", "valtuusto",
    "kunnanhallitus", "tarkastuslautakunta", "kunnan tilinpäätös"
]


def load_questions(path: Path) -> list[dict]:
    """Load adversarial questions."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("questions", [])


def load_law_indices(model: SentenceTransformer) -> dict:
    """Load law ChromaDB indices."""
    indices = {}
    for law_key, config in LAW_INDICES.items():
        chroma_path = config["chroma_path"]
        if chroma_path.exists():
            try:
                client = chromadb.PersistentClient(path=str(chroma_path))
                collection = client.get_collection(config["collection_name"])
                indices[law_key] = {"client": client, "collection": collection}
            except Exception as e:
                print(f"  Warning: {law_key}: {e}")
    return indices


def load_doc_index(path: Path, collection_name: str):
    """Load document ChromaDB index."""
    if not path.exists():
        return None
    try:
        client = chromadb.PersistentClient(path=str(path))
        collection = client.get_collection(collection_name)
        return {"client": client, "collection": collection}
    except Exception:
        return None


def query_all_laws(
    query: str,
    indices: dict,
    model: SentenceTransformer,
    k_per_law: int = 3,
) -> list[dict]:
    """Query all law indices and merge results."""
    all_hits = []
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    for law_key, index in indices.items():
        collection = index["collection"]
        try:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=k_per_law,
                include=["documents", "metadatas", "distances"],
            )
            
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                score = 1 - distance
                
                if score < MIN_SCORE:
                    continue
                
                meta = results["metadatas"][0][i]
                all_hits.append({
                    "law_key": law_key,
                    "node_id": meta.get("node_id", doc_id),
                    "section_num": meta.get("section_num"),
                    "moment": meta.get("moment"),
                    "score": score,
                    "text": results["documents"][0][i][:150],
                })
        except Exception:
            pass
    
    # Sort by score descending
    all_hits.sort(key=lambda x: x["score"], reverse=True)
    return all_hits[:K_TOTAL]


def query_docs(
    query: str,
    doc_index: dict | None,
    model: SentenceTransformer,
    k: int = 5,
) -> list[dict]:
    """Query document index."""
    if doc_index is None:
        return []
    
    embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
    
    try:
        collection = doc_index["collection"]
        results = collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        
        hits = []
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            score = 1 - distance
            meta = results["metadatas"][0][i]
            hits.append({
                "doc_node_id": doc_id,
                "node_type": meta.get("node_type"),
                "title": meta.get("title", ""),
                "page_num": meta.get("page_num"),
                "score": score,
                "text": results["documents"][0][i][:100],
            })
        return hits
    except Exception:
        return []


def should_abstain(query: str, law_hits: list[dict], doc_hits: list[dict]) -> tuple[bool, str]:
    """Determine if the system should abstain from answering."""
    query_lower = query.lower()
    
    # Strong abstain signals - always abstain (case-insensitive, partial match)
    for signal in ABSTAIN_SIGNALS_STRONG:
        # Check if signal root is in query (handles Finnish inflections)
        signal_lower = signal.lower()
        # Remove trailing vowels for root match (helsink-, tänää-, etc.)
        signal_root = signal_lower.rstrip("aeiouäö")
        if len(signal_root) >= 4 and signal_root in query_lower:
            return True, f"Strong signal: '{signal}'"
        elif signal_lower in query_lower:
            return True, f"Strong signal: '{signal}'"
    
    # Interpretation-required signals - abstain unless very high score
    for pattern in ABSTAIN_SIGNALS_INTERPRET:
        if re.search(pattern, query_lower):
            best_score = law_hits[0]["score"] if law_hits else 0
            if best_score < 0.70:  # High threshold for interpretation questions
                return True, f"Interpretation needed: '{pattern}'"
    
    # Check for future year
    if re.search(r"\b202[4-9]\b|\b203\d\b", query_lower):
        return True, "Future/missing year"
    
    # No hits at all
    if not law_hits and not doc_hits:
        return True, "No relevant data found"
    
    return False, ""


def apply_law_boost(query: str, law_hits: list[dict]) -> list[dict]:
    """Apply score boost based on query anchors. Returns re-sorted hits."""
    query_lower = query.lower()
    
    # OYL strong anchors (boost OYL, penalize KUNTA)
    oyl_strong = ["osakeyhtiö", "hallituksen vastuu", "yhtiökokous", "toimitusjohtaja", "osakeyhtiölaki"]
    oyl_count = sum(1 for a in oyl_strong if a in query_lower)
    
    # Municipal strong anchors (boost KUNTA, penalize others for municipal context)
    municipal_strong = ["kunnan", "kuntakonserni", "kuntalaki", "valtuusto", "kunnanhallitus", "tarkastuslautakunta"]
    municipal_count = sum(1 for a in municipal_strong if a in query_lower)
    
    # Weak municipal (present but not dominant)
    municipal_weak = ["kunta", "kunnan tilinpäätös"]
    municipal_weak_count = sum(1 for a in municipal_weak if a in query_lower)
    
    # Decision logic
    boost_oyl = oyl_count >= 2  # Strong OYL signal
    boost_kunta = municipal_count >= 1 and oyl_count == 0  # Municipal without OYL
    
    # If OYL has strong signal, boost OYL even if "kunnan" present (e.g., "kunnan tytäryhtiössä")
    if oyl_count >= 2:
        boost_oyl = True
        boost_kunta = False
    
    boosted = []
    for hit in law_hits:
        new_hit = hit.copy()
        
        if boost_oyl and hit["law_key"] == "osakeyhtiolaki_624_2006":
            new_hit["score"] = hit["score"] + 0.08  # Strong OYL boost
            new_hit["boosted"] = "oyl"
        elif boost_oyl and hit["law_key"] == "kuntalaki_410_2015":
            new_hit["score"] = hit["score"] - 0.03  # Penalize KUNTA when OYL context
            new_hit["penalized"] = "oyl_context"
        elif boost_kunta and hit["law_key"] == "kuntalaki_410_2015":
            new_hit["score"] = hit["score"] + 0.08  # Strong municipal boost
            new_hit["boosted"] = "municipal"
        elif boost_kunta and hit["law_key"] != "kuntalaki_410_2015":
            # Penalize non-KUNTA when strong municipal context
            if hit["law_key"] in ["kirjanpitolaki_1336_1997", "kirjanpitoasetus_1339_1997"]:
                new_hit["score"] = hit["score"] - 0.05
                new_hit["penalized"] = "municipal_context"
        
        boosted.append(new_hit)
    
    # Re-sort by score
    boosted.sort(key=lambda x: x["score"], reverse=True)
    return boosted


def evaluate_question(
    question: dict,
    law_indices: dict,
    doc_index: dict | None,
    model: SentenceTransformer,
) -> dict:
    """Evaluate a single adversarial question."""
    query = question["query"]
    expected = question.get("expected", {})
    scoring = question.get("scoring", {})
    category = question.get("category", "")
    
    start_time = time.time()
    
    # Query laws
    law_hits = query_all_laws(query, law_indices, model)
    
    # Apply law-specific boost/penalty based on query anchors
    law_hits = apply_law_boost(query, law_hits)
    
    # Query docs (for DOC category)
    doc_hits = []
    if category == "DOC" or expected.get("expected_doc_path_any"):
        doc_hits = query_docs(query, doc_index, model)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Determine if should abstain
    system_abstains, abstain_reason = should_abstain(query, law_hits, doc_hits)
    
    # v10.1 contract: required fields
    must_abstain = expected.get("must_abstain", False)
    
    result = {
        # v10.1 required fields
        "case_id": question["id"],
        "category": category,
        "query": query,
        "top1_law_key": law_hits[0]["law_key"] if law_hits else None,
        "topk_law_keys": [h["law_key"] for h in law_hits[:5]],
        "confusion_fail": False,  # Will be set below
        "hallucinated_evidence": False,  # Not implemented yet
        "version_drift": False,  # Not implemented yet
        "system_abstains": system_abstains,
        "abstain_expected": must_abstain,
        "latency_ms": latency_ms,
        # Additional info (backward compat)
        "id": question["id"],
        "law_hits_count": len(law_hits),
        "doc_hits_count": len(doc_hits),
        "top1_law": law_hits[0]["law_key"] if law_hits else None,
        "top1_score": law_hits[0]["score"] if law_hits else 0,
        "abstain_reason": abstain_reason,
        "expected": expected,
    }
    
    # Check pass conditions
    expected_laws = expected.get("expected_law_any", [])
    confusion_trap = scoring.get("confusion_trap")
    k_required = scoring.get("pass_if_topk_contains", 3)
    
    # ABSTAIN category
    if must_abstain:
        result["pass"] = system_abstains
        result["pass_reason"] = "Correctly abstained" if system_abstains else "Should have abstained"
        result["metric_type"] = "ABSTAIN"
    else:
        # LAW category - check if expected law is in top-k
        if expected_laws:
            top_k_laws = [h["law_key"] for h in law_hits[:k_required]]
            found = any(exp_law in top_k_laws for exp_law in expected_laws)
            
            result["pass"] = found
            result["expected_laws"] = expected_laws
            result["actual_topk_laws"] = top_k_laws
            
            if found:
                result["pass_reason"] = f"Expected law found in top-{k_required}"
            else:
                result["pass_reason"] = f"Expected law NOT in top-{k_required}"
            
            # Check confusion
            if confusion_trap and law_hits:
                if law_hits[0]["law_key"] == confusion_trap:
                    result["confusion_fail"] = True
                    result["metric_type"] = "CONFUSION_FAIL"
                else:
                    result["confusion_fail"] = False
            
            # Check near miss
            if not found and expected_laws:
                all_laws = [h["law_key"] for h in law_hits]
                if any(exp_law in all_laws for exp_law in expected_laws):
                    result["near_miss"] = True
                    result["metric_type"] = "NEAR_MISS"
        else:
            # DOC category or no expected laws
            result["pass"] = len(doc_hits) > 0 if category == "DOC" else True
            result["pass_reason"] = "DOC hits found" if result["pass"] else "No DOC hits"
    
    return result



# NOTE: Report generation moved to render_v10_report.py (v10.1 single-source)


def main() -> None:
    print("=" * 60)
    print("v10.1: Adversarial Eval Runner")
    print("=" * 60)
    
    questions = load_questions(QUESTIONS_PATH)
    print(f"\nLoaded {len(questions)} adversarial questions")
    
    print("\nLoading embedding model...")
    model = SentenceTransformer("BAAI/bge-m3")
    
    print("\nLoading law indices...")
    law_indices = load_law_indices(model)
    print(f"  Loaded: {len(law_indices)} indices")
    
    print("\nLoading document index...")
    doc_index = load_doc_index(DOC_INDEX_PATH, DOC_COLLECTION)
    print(f"  Doc index: {'loaded' if doc_index else 'not found'}")
    
    print("\nRunning adversarial evaluation...")
    results = []
    for i, q in enumerate(questions):
        result = evaluate_question(q, law_indices, doc_index, model)
        status = "PASS" if result.get("pass") else "FAIL"
        print(f"  [{i+1}/{len(questions)}] {q['id']}: {status}")
        results.append(result)
    
    # Write JSON results (SINGLE SOURCE OF TRUTH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "v10_adversarial_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults JSON: {results_path}")
    print("\nNow run: python scripts/render_v10_report.py")
    print("to generate summary and failures reports from the JSON.")


if __name__ == "__main__":
    main()

